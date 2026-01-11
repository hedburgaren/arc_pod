# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields, api


class ProductTemplate(models.Model):
    """Extend product.template to add POD mappings through variants."""

    _inherit = 'product.template'

    pod_mapping_count = fields.Integer(
        string='POD Mapping Count',
        compute='_compute_pod_mapping_count',
    )

    @api.depends('product_variant_ids.pod_mapping_ids')
    def _compute_pod_mapping_count(self):
        """Compute count of POD mappings across all variants."""
        for record in self:
            total_count = sum(
                variant.pod_mapping_count
                for variant in record.product_variant_ids
            )
            record.pod_mapping_count = total_count

    def action_view_pod_mappings(self):
        """Open POD mappings for all variants of this template."""
        self.ensure_one()
        variant_ids = self.product_variant_ids.ids
        return {
            'name': 'POD Mappings',
            'type': 'ir.actions.act_window',
            'res_model': 'pod.product.mapping',
            'view_mode': 'tree,form',
            'domain': [('odoo_product_id', 'in', variant_ids)],
            'context': {'default_odoo_product_id': variant_ids[0] if variant_ids else False},
        }

