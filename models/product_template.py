# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields


class ProductTemplate(models.Model):
    """Extend product.template to add POD mappings."""

    _inherit = 'product.template'

    pod_mapping_ids = fields.One2many(
        comodel_name='pod.product.mapping',
        inverse_name='odoo_product_id',
        string='POD Mappings',
        help='Print-on-demand product mappings',
    )

    def action_open_pod_catalog_wizard(self):
        """Open catalog wizard with current product pre-filled."""
        self.ensure_one()
        return {
            'name': 'Add POD Mapping',
            'type': 'ir.actions.act_window',
            'res_model': 'pod.catalog.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_odoo_product_id': self.id,
            },
        }
