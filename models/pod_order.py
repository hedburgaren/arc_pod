# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PodOrder(models.Model):
    """Model for managing POD orders sent to providers."""

    _name = 'pod.order'
    _description = 'POD Order'
    _order = 'created_date desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
    )
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade',
    )
    provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='POD Provider',
        required=True,
        ondelete='restrict',
    )
    external_order_id = fields.Char(
        string='External Order ID',
        readonly=True,
        help='POD provider order ID after submission',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('failed', 'Failed'),
            ('completed', 'Completed'),
        ],
        string='State',
        required=True,
        default='draft',
    )
    tracking_number = fields.Char(
        string='Tracking Number',
        readonly=True,
    )
    tracking_url = fields.Char(
        string='Tracking URL',
        readonly=True,
    )
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
    )
    last_sync = fields.Datetime(
        string='Last Sync',
        readonly=True,
    )
    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now,
        readonly=True,
    )
    pod_order_data = fields.Text(
        string='POD Order Data',
        help='JSON storage for API response',
    )

    _sql_constraints = [
        (
            'unique_external_order_provider',
            'UNIQUE(external_order_id, provider_id)',
            'External order ID must be unique per provider!',
        ),
    ]

    @api.depends('sale_order_id', 'provider_id')
    def _compute_name(self):
        """Compute display name from sale order and provider."""
        for record in self:
            if record.sale_order_id and record.provider_id:
                record.name = f"{record.sale_order_id.name} - {record.provider_id.name}"
            else:
                record.name = _('POD Order')

    def action_send_to_provider(self):
        """Send order to POD API."""
        self.ensure_one()

        # Validate state
        if self.state != 'draft':
            raise UserError(_("Only draft orders can be sent to provider."))

        # Get API configuration
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        api_key = IrConfigParameter.get_param('arc_pod.api_key', default='')
        shop_id = IrConfigParameter.get_param('arc_pod.shop_id', default='')

        if not api_key:
            raise UserError(_("API Key is not configured. Please configure it in Settings > ARC POD."))

        try:
            # Set state to pending
            self.write({'state': 'pending'})
            self.env.cr.commit()

            # Transform order data
            from .pod_order_transformer import PODOrderTransformer
            transformer = PODOrderTransformer(self.env)
            
            if self.provider_id.code == 'printify':
                order_data = transformer.transform_for_printify(self.sale_order_id)
                from .printify_api import PrintifyAPI
                if not shop_id:
                    raise UserError(_("Shop ID is required for Printify. Please configure it in Settings > ARC POD."))
                api_client = PrintifyAPI(api_key, shop_id)
            elif self.provider_id.code == 'gelato':
                order_data = transformer.transform_for_gelato(self.sale_order_id)
                from .gelato_api import GelatoAPI
                api_client = GelatoAPI(api_key)
            elif self.provider_id.code == 'printful':
                order_data = transformer.transform_for_printful(self.sale_order_id)
                from .printful_api import PrintfulAPI
                api_client = PrintfulAPI(api_key)
            else:
                raise UserError(_("Unsupported provider: %s") % self.provider_id.code)

            # Call provider API
            _logger.info("Sending order %s to %s", self.name, self.provider_id.name)
            result = api_client.create_order(order_data)

            if result.get('success'):
                # Update order with success data
                self.write({
                    'state': 'sent',
                    'external_order_id': result.get('order_id'),
                    'last_sync': fields.Datetime.now(),
                    'pod_order_data': json.dumps(result, indent=2),
                })
                _logger.info("Order %s sent successfully to %s", self.name, self.provider_id.name)
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Order sent successfully to %s") % self.provider_id.name,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                # Handle failure
                error_msg = result.get('message', _('Unknown error occurred'))
                self.write({
                    'state': 'failed',
                    'error_message': error_msg,
                    'pod_order_data': json.dumps(result, indent=2),
                })
                
                # Log error
                self.env['pod.error.log'].create({
                    'provider_id': self.provider_id.id,
                    'error_message': _("Failed to send order %s: %s") % (self.name, error_msg),
                    'error_code': 'ORDER_SEND_FAILED',
                    'request_endpoint': 'create_order',
                })
                
                raise UserError(_("Failed to send order: %s") % error_msg)

        except Exception as e:
            _logger.error("Error sending order %s: %s", self.name, str(e))
            
            # Update order state to failed
            self.write({
                'state': 'failed',
                'error_message': str(e),
            })
            
            # Log error
            self.env['pod.error.log'].create({
                'provider_id': self.provider_id.id,
                'error_message': _("Failed to send order %s: %s") % (self.name, str(e)),
                'error_code': 'ORDER_SEND_ERROR',
                'request_endpoint': 'create_order',
            })
            
            raise UserError(_("Failed to send order: %s") % str(e))

    def action_fetch_status(self):
        """Retrieve tracking/status from POD API."""
        self.ensure_one()

        # Validate state
        if self.state not in ['sent', 'completed']:
            raise UserError(_("Can only fetch status for sent or completed orders."))

        if not self.external_order_id:
            raise UserError(_("External order ID is missing. Cannot fetch status."))

        # Get API configuration
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        api_key = IrConfigParameter.get_param('arc_pod.api_key', default='')
        shop_id = IrConfigParameter.get_param('arc_pod.shop_id', default='')

        if not api_key:
            raise UserError(_("API Key is not configured. Please configure it in Settings > ARC POD."))

        try:
            # Get API client
            if self.provider_id.code == 'printify':
                from .printify_api import PrintifyAPI
                if not shop_id:
                    raise UserError(_("Shop ID is required for Printify. Please configure it in Settings > ARC POD."))
                api_client = PrintifyAPI(api_key, shop_id)
            elif self.provider_id.code == 'gelato':
                from .gelato_api import GelatoAPI
                api_client = GelatoAPI(api_key)
            elif self.provider_id.code == 'printful':
                from .printful_api import PrintfulAPI
                api_client = PrintfulAPI(api_key)
            else:
                raise UserError(_("Unsupported provider: %s") % self.provider_id.code)

            # Fetch status
            _logger.info("Fetching status for order %s from %s", self.name, self.provider_id.name)
            status_data = api_client.get_order_status(self.external_order_id)

            # Update tracking information
            vals = {
                'last_sync': fields.Datetime.now(),
            }

            if status_data.get('tracking_number'):
                vals['tracking_number'] = status_data['tracking_number']
            
            if status_data.get('tracking_url'):
                vals['tracking_url'] = status_data['tracking_url']
            
            # Update state if completed
            if status_data.get('status') in ['completed', 'shipped', 'delivered']:
                vals['state'] = 'completed'

            self.write(vals)
            _logger.info("Status updated for order %s", self.name)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Status updated successfully"),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error("Error fetching status for order %s: %s", self.name, str(e))
            
            # Log error
            self.env['pod.error.log'].create({
                'provider_id': self.provider_id.id,
                'error_message': _("Failed to fetch status for order %s: %s") % (self.name, str(e)),
                'error_code': 'STATUS_FETCH_ERROR',
                'request_endpoint': 'get_order_status',
            })
            
            raise UserError(_("Failed to fetch status: %s") % str(e))

    def action_retry(self):
        """Reset to draft and retry sending."""
        self.ensure_one()

        if self.state != 'failed':
            raise UserError(_("Only failed orders can be retried."))

        self.write({
            'state': 'draft',
            'error_message': False,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _("Order reset to draft. You can now send it again."),
                'type': 'info',
                'sticky': False,
            }
        }

    @api.model
    def cron_fetch_all_pending_status(self):
        """Cron job to fetch status for all sent orders."""
        _logger.info("Starting cron job to fetch POD order statuses")
        
        # Find all sent orders
        sent_orders = self.search([('state', '=', 'sent')])
        _logger.info("Found %s sent orders to sync", len(sent_orders))
        
        success_count = 0
        error_count = 0
        
        for order in sent_orders:
            try:
                order.action_fetch_status()
                success_count += 1
            except Exception as e:
                _logger.error("Error syncing order %s: %s", order.name, str(e))
                error_count += 1
                
                # Log error
                self.env['pod.error.log'].create({
                    'provider_id': order.provider_id.id,
                    'error_message': _("Cron failed to sync order %s: %s") % (order.name, str(e)),
                    'error_code': 'CRON_SYNC_ERROR',
                    'request_endpoint': 'cron_fetch_all_pending_status',
                })
        
        _logger.info(
            "Cron job completed. Synced: %s, Errors: %s",
            success_count,
            error_count
        )
