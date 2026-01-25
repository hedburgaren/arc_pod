# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PodOrder(models.Model):
    """Model for POD orders synced to providers."""

    _name = 'pod.order'
    _description = 'POD Order'
    _order = 'sent_date desc, id desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        readonly=True,
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
        help='Order ID from POD provider',
    )
    status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('processing', 'Processing'),
            ('shipped', 'Shipped'),
            ('delivered', 'Delivered'),
            ('error', 'Error'),
        ],
        string='Status',
        required=True,
        default='pending',
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
    sent_date = fields.Datetime(
        string='Sent Date',
        readonly=True,
    )
    last_status_update = fields.Datetime(
        string='Last Status Update',
        readonly=True,
    )

    _sql_constraints = [
        (
            'unique_sale_order_provider',
            'UNIQUE(sale_order_id, provider_id)',
            'Only one POD order per sale order and provider is allowed!',
        ),
    ]

    @api.depends('sale_order_id', 'provider_id')
    def _compute_name(self):
        """Compute name from sale order and provider."""
        for record in self:
            if record.sale_order_id and record.provider_id:
                record.name = f"{record.sale_order_id.name} - {record.provider_id.name}"
            else:
                record.name = _('New POD Order')

    def action_send_to_provider(self):
        """Send order to POD provider."""
        self.ensure_one()
        
        try:
            # Validate before sending
            self._validate_order_data()
            
            # Prepare order data
            order_data = self._prepare_order_data()
            
            # Get API client
            api_client = self._get_api_client()
            
            # Send order to provider
            _logger.info("Sending order %s to provider %s", self.sale_order_id.name, self.provider_id.name)
            result = api_client.create_order(order_data)
            
            if result.get('success'):
                self.write({
                    'status': 'sent',
                    'external_order_id': result.get('order_id'),
                    'sent_date': fields.Datetime.now(),
                    'last_status_update': fields.Datetime.now(),
                    'error_message': False,
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Order successfully sent to %s") % self.provider_id.name,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_msg = result.get('message', _('Unknown error'))
                self._log_error(error_msg, 'SEND_ORDER_FAILED')
                raise UserError(_("Failed to send order: %s") % error_msg)
                
        except Exception as e:
            error_msg = str(e)
            _logger.error("Error sending order to provider: %s", error_msg)
            self._log_error(error_msg, 'SEND_ORDER_ERROR')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Error sending order: %s") % error_msg,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_update_status(self):
        """Fetch latest status from provider."""
        self.ensure_one()
        
        if not self.external_order_id:
            raise UserError(_("Cannot update status: Order has not been sent to provider yet."))
        
        try:
            # Get API client
            api_client = self._get_api_client()
            
            # Get order status
            _logger.info("Updating status for order %s from provider %s", self.sale_order_id.name, self.provider_id.name)
            result = api_client.get_order_status(self.external_order_id)
            
            # Map provider status to standard status
            mapped_status = self._map_provider_status(result.get('status', ''))
            
            update_vals = {
                'status': mapped_status,
                'last_status_update': fields.Datetime.now(),
            }
            
            if result.get('tracking_number'):
                update_vals['tracking_number'] = result['tracking_number']
            
            if result.get('tracking_url'):
                update_vals['tracking_url'] = result['tracking_url']
            
            self.write(update_vals)
            
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
            error_msg = str(e)
            _logger.error("Error updating order status: %s", error_msg)
            self._log_error(error_msg, 'UPDATE_STATUS_ERROR')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Error updating status: %s") % error_msg,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_retry(self):
        """Retry failed orders."""
        self.ensure_one()
        
        if self.status != 'error':
            raise UserError(_("Can only retry failed orders."))
        
        # Reset status and clear error
        self.write({
            'status': 'pending',
            'error_message': False,
        })
        
        # Try to send again
        return self.action_send_to_provider()

    def _prepare_order_data(self):
        """Format order data for API."""
        self.ensure_one()
        
        # Get shipping address
        partner = self.sale_order_id.partner_shipping_id or self.sale_order_id.partner_id
        
        # Prepare recipient data
        recipient = {
            'name': partner.name or '',
            'address1': partner.street or '',
            'city': partner.city or '',
            'zip': partner.zip or '',
            'country': partner.country_id.code if partner.country_id else '',
            'email': partner.email or '',
            'phone': partner.phone or partner.mobile or '',
        }
        
        # Add optional fields if available
        if partner.street2:
            recipient['address2'] = partner.street2
        if partner.state_id:
            recipient['state'] = partner.state_id.code or partner.state_id.name
        
        # Prepare items from order lines with POD mappings
        items = []
        for line in self.sale_order_id.order_line:
            # Find POD mapping for this product and provider
            mapping = self.env['pod.product.mapping'].search([
                ('odoo_product_id', '=', line.product_id.id),
                ('provider_id', '=', self.provider_id.id),
            ], limit=1)
            
            if mapping and mapping.pod_product_id:
                item = {
                    'product_id': mapping.pod_product_id.external_id,
                    'quantity': int(line.product_uom_qty),
                }
                
                # Add variant ID if available
                if mapping.pod_variant_id:
                    item['variant_id'] = mapping.pod_variant_id.external_id
                
                items.append(item)
        
        return {
            'recipient': recipient,
            'items': items,
        }

    def _validate_order_data(self):
        """Validate order data before sending."""
        self.ensure_one()
        
        # Validate shipping address
        partner = self.sale_order_id.partner_shipping_id or self.sale_order_id.partner_id
        
        if not partner.name:
            raise UserError(_("Customer name is required"))
        if not partner.street:
            raise UserError(_("Street address is required"))
        if not partner.city:
            raise UserError(_("City is required"))
        if not partner.zip:
            raise UserError(_("ZIP code is required"))
        if not partner.country_id:
            raise UserError(_("Country is required"))
        
        # Validate order lines have POD mappings
        has_mapped_products = False
        for line in self.sale_order_id.order_line:
            mapping = self.env['pod.product.mapping'].search([
                ('odoo_product_id', '=', line.product_id.id),
                ('provider_id', '=', self.provider_id.id),
            ], limit=1)
            
            if mapping:
                has_mapped_products = True
                break
        
        if not has_mapped_products:
            raise UserError(_("No order lines have POD product mappings for provider %s") % self.provider_id.name)
        
        # Validate provider is configured
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        api_key = IrConfigParameter.get_param('arc_pod.api_key', default='')
        
        if not api_key:
            raise UserError(_("API Key is not configured. Please configure it in Settings > ARC POD."))
        
        # Validate shop_id for Printify
        if self.provider_id.code == 'printify':
            shop_id = IrConfigParameter.get_param('arc_pod.shop_id', default='')
            if not shop_id:
                raise UserError(_("Shop ID is required for Printify. Please configure it in Settings > ARC POD."))

    def _get_api_client(self):
        """Get appropriate API client for provider."""
        self.ensure_one()
        
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        api_key = IrConfigParameter.get_param('arc_pod.api_key', default='')
        
        if self.provider_id.code == 'printify':
            from .printify_api import PrintifyAPI
            shop_id = IrConfigParameter.get_param('arc_pod.shop_id', default='')
            return PrintifyAPI(api_key, shop_id)
        elif self.provider_id.code == 'gelato':
            from .gelato_api import GelatoAPI
            return GelatoAPI(api_key)
        elif self.provider_id.code == 'printful':
            from .printful_api import PrintfulAPI
            return PrintfulAPI(api_key)
        else:
            raise UserError(_("Unsupported provider: %s") % self.provider_id.code)

    def _map_provider_status(self, provider_status):
        """Map provider-specific status to standard status."""
        self.ensure_one()
        
        # Normalize status string
        status_lower = str(provider_status).lower()
        
        # Common status mappings
        if status_lower in ['pending', 'draft', 'created']:
            return 'sent'
        elif status_lower in ['processing', 'in_progress', 'fulfillment', 'production']:
            return 'processing'
        elif status_lower in ['shipped', 'transit', 'dispatched']:
            return 'shipped'
        elif status_lower in ['delivered', 'completed', 'fulfilled']:
            return 'delivered'
        elif status_lower in ['error', 'failed', 'canceled', 'cancelled']:
            return 'error'
        else:
            # Default to processing for unknown statuses
            return 'processing'

    def _log_error(self, error_message, error_code):
        """Log error to pod.error.log."""
        self.ensure_one()
        
        self.env['pod.error.log'].create({
            'provider_id': self.provider_id.id,
            'error_message': error_message,
            'error_code': error_code,
            'request_endpoint': 'order_sync',
            'timestamp': fields.Datetime.now(),
        })
        
        self.write({
            'status': 'error',
            'error_message': error_message,
            'last_status_update': fields.Datetime.now(),
        })

    def _update_status_silent(self):
        """Fetch latest status from provider without returning UI notifications."""
        self.ensure_one()
        
        if not self.external_order_id:
            _logger.warning("Cannot update status for order %s: No external order ID", self.name)
            return False
        
        try:
            # Get API client
            api_client = self._get_api_client()
            
            # Get order status
            result = api_client.get_order_status(self.external_order_id)
            
            # Map provider status to standard status
            mapped_status = self._map_provider_status(result.get('status', ''))
            
            update_vals = {
                'status': mapped_status,
                'last_status_update': fields.Datetime.now(),
            }
            
            if result.get('tracking_number'):
                update_vals['tracking_number'] = result['tracking_number']
            
            if result.get('tracking_url'):
                update_vals['tracking_url'] = result['tracking_url']
            
            self.write(update_vals)
            return True
            
        except Exception as e:
            error_msg = str(e)
            _logger.error("Error updating order status for %s: %s", self.name, error_msg)
            self._log_error(error_msg, 'UPDATE_STATUS_ERROR')
            return False

    @api.model
    def _cron_update_pod_orders(self):
        """Scheduled action to update POD order statuses."""
        _logger.info("Starting scheduled POD order status update")
        
        # Find all orders that need status updates
        orders = self.search([
            ('status', 'in', ['sent', 'processing', 'shipped']),
            ('external_order_id', '!=', False),
        ])
        
        _logger.info("Found %d orders to update", len(orders))
        
        success_count = 0
        error_count = 0
        
        for order in orders:
            if order._update_status_silent():
                success_count += 1
            else:
                error_count += 1
        
        _logger.info(
            "Completed POD order status update: %d successful, %d errors",
            success_count,
            error_count
        )
