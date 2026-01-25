# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """Extend sale.order to support POD orders."""

    _inherit = 'sale.order'

    pod_order_ids = fields.One2many(
        comodel_name='pod.order',
        inverse_name='sale_order_id',
        string='POD Orders',
    )
    has_pod_mapping = fields.Boolean(
        string='Has POD Mapping',
        compute='_compute_has_pod_mapping',
        store=True,
    )
    pod_order_count = fields.Integer(
        string='POD Order Count',
        compute='_compute_pod_order_count',
    )

    @api.depends('order_line', 'order_line.product_id', 'order_line.product_id.pod_mapping_ids')
    def _compute_has_pod_mapping(self):
        """Check if any order line has POD mapping."""
        for record in self:
            has_mapping = False
            for line in record.order_line:
                if line.product_id and line.product_id.pod_mapping_ids:
                    has_mapping = True
                    break
            record.has_pod_mapping = has_mapping

    @api.depends('pod_order_ids')
    def _compute_pod_order_count(self):
        """Compute count of POD orders."""
        for record in self:
            record.pod_order_count = len(record.pod_order_ids)

    def action_confirm(self):
        """Override to auto-create POD orders if mappings exist."""
        # Call parent method
        res = super(SaleOrder, self).action_confirm()
        
        # Create POD orders for confirmed orders with mappings
        for order in self:
            if order.has_pod_mapping and not order.pod_order_ids:
                try:
                    order._create_pod_orders()
                except Exception as e:
                    _logger.error("Error creating POD orders for %s: %s", order.name, str(e))
                    # Don't block order confirmation if POD order creation fails
        
        return res

    def action_open_pod_orders(self):
        """Open tree view of POD orders."""
        self.ensure_one()
        
        return {
            'name': _('POD Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'pod.order',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }

    def _create_pod_orders(self):
        """Create pod.order records per provider."""
        self.ensure_one()
        
        if not self.has_pod_mapping:
            _logger.info("No POD mappings found for order %s", self.name)
            return
        
        # Group order lines by provider
        provider_lines = {}
        for line in self.order_line:
            if line.product_id and line.product_id.pod_mapping_ids:
                for mapping in line.product_id.pod_mapping_ids:
                    provider_id = mapping.provider_id.id
                    if provider_id not in provider_lines:
                        provider_lines[provider_id] = []
                    provider_lines[provider_id].append(line)
        
        # Create one pod.order per provider
        pod_orders = []
        for provider_id, lines in provider_lines.items():
            provider = self.env['pod.provider'].browse(provider_id)
            
            pod_order = self.env['pod.order'].create({
                'sale_order_id': self.id,
                'provider_id': provider_id,
                'state': 'draft',
            })
            pod_orders.append(pod_order)
            
            _logger.info(
                "Created POD order %s for provider %s with %s lines",
                pod_order.name,
                provider.name,
                len(lines)
            )
        
        return pod_orders
