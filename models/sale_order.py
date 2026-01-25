# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """Extend sale.order with POD order functionality."""

    _inherit = 'sale.order'

    pod_order_ids = fields.One2many(
        comodel_name='pod.order',
        inverse_name='sale_order_id',
        string='POD Orders',
    )
    pod_order_count = fields.Integer(
        string='POD Order Count',
        compute='_compute_pod_order_count',
    )
    has_pod_products = fields.Boolean(
        string='Has POD Products',
        compute='_compute_has_pod_products',
        store=True,
    )

    @api.depends('pod_order_ids')
    def _compute_pod_order_count(self):
        """Compute count of POD orders."""
        for order in self:
            order.pod_order_count = len(order.pod_order_ids)

    @api.depends('order_line', 'order_line.product_id')
    def _compute_has_pod_products(self):
        """Check if order has products with POD mappings."""
        for order in self:
            has_pod = False
            for line in order.order_line:
                # Check if this product has any POD mapping
                mapping = self.env['pod.product.mapping'].search([
                    ('odoo_product_id', '=', line.product_id.id),
                ], limit=1)
                
                if mapping:
                    has_pod = True
                    break
            
            order.has_pod_products = has_pod

    def action_confirm(self):
        """Override to auto-send to POD if has_pod_products."""
        result = super(SaleOrder, self).action_confirm()
        
        # After confirming the order, check if we need to create POD orders
        for order in self:
            if order.has_pod_products:
                try:
                    order._create_pod_orders()
                except Exception as e:
                    _logger.error("Error creating POD orders for %s: %s", order.name, str(e))
                    # Show error notification but don't prevent order confirmation
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _("Order confirmed but POD sync failed: %s") % str(e),
                            'type': 'warning',
                            'sticky': True,
                            'next': result,
                        }
                    }
        
        return result

    def action_view_pod_orders(self):
        """Open POD orders related to this sale order."""
        self.ensure_one()
        
        action = self.env.ref('arc_pod.action_pod_order').read()[0]
        
        if self.pod_order_count == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.pod_order_ids.id
        else:
            action['domain'] = [('sale_order_id', '=', self.id)]
        
        return action

    def _create_pod_orders(self):
        """Create POD order records for mapped products."""
        self.ensure_one()
        
        _logger.info("Creating POD orders for sale order %s", self.name)
        
        # Group order lines by provider
        providers_with_products = {}
        
        for line in self.order_line:
            # Get all mappings for this product
            mappings = self.env['pod.product.mapping'].search([
                ('odoo_product_id', '=', line.product_id.id),
            ])
            
            for mapping in mappings:
                provider_id = mapping.provider_id.id
                if provider_id not in providers_with_products:
                    providers_with_products[provider_id] = True
        
        if not providers_with_products:
            _logger.info("No POD products found in order %s", self.name)
            return
        
        # Create POD order for each provider
        created_orders = self.env['pod.order']
        failed_providers = []
        
        for provider_id in providers_with_products.keys():
            provider = self.env['pod.provider'].browse(provider_id)
            
            # Check if POD order already exists
            existing_order = self.env['pod.order'].search([
                ('sale_order_id', '=', self.id),
                ('provider_id', '=', provider_id),
            ], limit=1)
            
            if existing_order:
                _logger.info("POD order already exists for provider %s", provider.name)
                continue
            
            try:
                # Create POD order
                pod_order = self.env['pod.order'].create({
                    'sale_order_id': self.id,
                    'provider_id': provider_id,
                    'status': 'pending',
                })
                
                # Try to send to provider
                pod_order.action_send_to_provider()
                created_orders |= pod_order
                
            except Exception as e:
                _logger.error("Failed to create/send POD order for provider %s: %s", provider.name, str(e))
                failed_providers.append(provider.name)
        
        # Log notification results
        if created_orders and not failed_providers:
            _logger.info("Successfully created and sent %d POD order(s) for %s", len(created_orders), self.name)
        elif created_orders and failed_providers:
            _logger.warning("Created %d POD order(s) for %s. Failed for: %s", 
                          len(created_orders), self.name, ', '.join(failed_providers))
        elif failed_providers:
            _logger.error("Failed to create POD orders for %s: %s", self.name, ', '.join(failed_providers))
