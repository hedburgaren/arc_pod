# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from odoo import models, fields, api, _
from .printify_api import PrintifyAPI
from .gelato_api import GelatoAPI
from .printful_api import PrintfulAPI

_logger = logging.getLogger(__name__)


class PodConfig(models.TransientModel):
    """Configuration settings for ARC POD integration."""

    _name = 'pod.config'
    _inherit = 'res.config.settings'
    _description = 'POD Configuration Settings'

    selected_provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='Selected Provider',
        help='Choose the print-on-demand service provider',
    )
    api_key = fields.Char(
        string='API Key',
        help='API key for the selected provider',
    )
    api_secret = fields.Char(
        string='API Secret',
        help='API secret (only for providers that require it)',
    )
    connection_status = fields.Selection(
        selection=[
            ('not_tested', 'Not Tested'),
            ('success', 'Success'),
            ('failed', 'Failed'),
        ],
        string='Connection Status',
        default='not_tested',
        readonly=True,
    )
    connection_message = fields.Text(
        string='Connection Message',
        readonly=True,
    )
    last_connection_test = fields.Datetime(
        string='Last Connection Test',
        readonly=True,
        help='Timestamp of the last connection test',
    )
    error_log_ids = fields.Many2many(
        comodel_name='pod.error.log',
        string='Error Logs',
        compute='_compute_error_log_ids',
        readonly=True,
    )

    @api.depends('selected_provider_id')
    def _compute_error_log_ids(self):
        """Compute error logs for the selected provider."""
        for record in self:
            if record.selected_provider_id:
                error_logs = self.env['pod.error.log'].search([
                    ('provider_id', '=', record.selected_provider_id.id)
                ], limit=3, order='timestamp desc')
                record.error_log_ids = error_logs
            else:
                record.error_log_ids = False

    @api.model
    def get_values(self):
        """Retrieve configuration values from system parameters."""
        res = super(PodConfig, self).get_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()

        provider_id = IrConfigParameter.get_param('arc_pod.selected_provider_id', default=False)
        last_test = IrConfigParameter.get_param('arc_pod.last_connection_test', default=False)
        
        res.update(
            selected_provider_id=int(provider_id) if provider_id else False,
            api_key=IrConfigParameter.get_param('arc_pod.api_key', default=''),
            api_secret=IrConfigParameter.get_param('arc_pod.api_secret', default=''),
            connection_status=IrConfigParameter.get_param('arc_pod.connection_status', default='not_tested'),
            connection_message=IrConfigParameter.get_param('arc_pod.connection_message', default=''),
            last_connection_test=last_test if last_test else False,
        )
        return res

    def set_values(self):
        """Store configuration values in system parameters."""
        super(PodConfig, self).set_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()

        IrConfigParameter.set_param('arc_pod.selected_provider_id', self.selected_provider_id.id or False)
        IrConfigParameter.set_param('arc_pod.api_key', self.api_key or '')
        IrConfigParameter.set_param('arc_pod.api_secret', self.api_secret or '')
        IrConfigParameter.set_param('arc_pod.connection_status', self.connection_status or 'not_tested')
        IrConfigParameter.set_param('arc_pod.connection_message', self.connection_message or '')
        IrConfigParameter.set_param('arc_pod.last_connection_test', self.last_connection_test or False)

    def action_test_connection(self):
        """
        Test connection to the selected provider.
        Instantiates the correct API client and calls test_connection().
        """
        self.ensure_one()

        # Validate that a provider is selected
        if not self.selected_provider_id:
            self.write({
                'connection_status': 'failed',
                'connection_message': _('No provider selected'),
                'last_connection_test': fields.Datetime.now(),
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Please select a provider first'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Validate that an API key is provided
        if not self.api_key:
            self.write({
                'connection_status': 'failed',
                'connection_message': _('No API key provided'),
                'last_connection_test': fields.Datetime.now(),
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Please provide an API key'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Get the provider code and instantiate the correct API client
        provider_code = self.selected_provider_id.code
        api_url = self.selected_provider_id.api_url

        try:
            # Instantiate the appropriate API client
            if provider_code == 'printify':
                api_client = PrintifyAPI(api_key=self.api_key, base_url=api_url)
            elif provider_code == 'gelato':
                api_client = GelatoAPI(api_key=self.api_key, base_url=api_url)
            elif provider_code == 'printful':
                api_client = PrintfulAPI(api_key=self.api_key, base_url=api_url)
            else:
                raise ValueError(_('Unknown provider: %s') % provider_code)

            # Test the connection
            _logger.info(f"Testing connection for provider: {provider_code}")
            result = api_client.test_connection()

            # Update connection status
            status = 'success' if result['success'] else 'failed'
            self.write({
                'connection_status': status,
                'connection_message': result['message'],
                'last_connection_test': fields.Datetime.now(),
            })

            # Log error if connection failed
            if not result['success']:
                self.env['pod.error.log'].sudo().create({
                    'provider_id': self.selected_provider_id.id,
                    'error_message': result['message'],
                    'error_code': '',  # Status code is included in the message
                    'request_endpoint': 'test_connection',
                    'timestamp': fields.Datetime.now(),
                })

            # Show notification
            notification_type = 'success' if result['success'] else 'danger'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': result['message'],
                    'type': notification_type,
                    'sticky': False,
                }
            }

        except Exception as e:
            error_message = _('Connection test failed: %s') % str(e)
            _logger.error(error_message)
            
            self.write({
                'connection_status': 'failed',
                'connection_message': error_message,
                'last_connection_test': fields.Datetime.now(),
            })

            # Log the error
            self.env['pod.error.log'].sudo().create({
                'provider_id': self.selected_provider_id.id,
                'error_message': error_message,
                'error_code': '',
                'request_endpoint': 'test_connection',
                'timestamp': fields.Datetime.now(),
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': error_message,
                    'type': 'danger',
                    'sticky': False,
                }
            }
