# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields, api, _


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

    @api.model
    def get_values(self):
        """Retrieve configuration values from system parameters."""
        res = super(PodConfig, self).get_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        
        provider_id = IrConfigParameter.get_param('arc_pod.selected_provider_id', default=False)
        res.update(
            selected_provider_id=int(provider_id) if provider_id else False,
            api_key=IrConfigParameter.get_param('arc_pod.api_key', default=''),
            api_secret=IrConfigParameter.get_param('arc_pod.api_secret', default=''),
            connection_status=IrConfigParameter.get_param('arc_pod.connection_status', default='not_tested'),
            connection_message=IrConfigParameter.get_param('arc_pod.connection_message', default=''),
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

    def action_test_connection(self):
        """
        Test connection to the selected provider.
        Placeholder method - actual implementation in future sprints.
        """
        self.ensure_one()
        self.write({
            'connection_status': 'not_tested',
            'connection_message': _('Connection test not implemented yet'),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Connection test not implemented yet'),
                'type': 'info',
                'sticky': False,
            }
        }
