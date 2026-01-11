# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields, api


class ProductProduct(models.Model):
    """Extend product.product to add POD mappings."""

    _inherit = 'product.product'

    pod_mapping_ids = fields.One2many(
        comodel_name='pod.product.mapping',
        inverse_name='odoo_product_id',
        string='POD Mappings',
        help='Print-on-demand product mappings',
    )
    has_pod_mapping = fields.Boolean(
        string='Has POD Mapping',
        compute='_compute_has_pod_mapping',
        store=True,
    )
    pod_mapping_count = fields.Integer(
        string='POD Mapping Count',
        compute='_compute_pod_mapping_count',
    )

    @api.depends('pod_mapping_ids')
    def _compute_has_pod_mapping(self):
        """Compute if product has any POD mappings."""
        for record in self:
            record.has_pod_mapping = bool(record.pod_mapping_ids)

    @api.depends('pod_mapping_ids')
    def _compute_pod_mapping_count(self):
        """Compute count of POD mappings."""
        for record in self:
            record.pod_mapping_count = len(record.pod_mapping_ids)

    def action_view_pod_mappings(self):
        """Open POD mappings for this product."""
        self.ensure_one()
        return {
            'name': 'POD Mappings',
            'type': 'ir.actions.act_window',
            'res_model': 'pod.product.mapping',
            'view_mode': 'tree,form',
            'domain': [('odoo_product_id', '=', self.id)],
            'context': {'default_odoo_product_id': self.id},
        }
