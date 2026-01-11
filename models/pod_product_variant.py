# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields, api


class PodProductVariant(models.Model):
    """Model representing POD product variants."""

    _name = 'pod.product.variant'
    _description = 'POD Product Variant'
    _order = 'product_id, name'

    name = fields.Char(
        string='Variant Name',
        compute='_compute_name',
        store=True,
    )
    product_id = fields.Many2one(
        comodel_name='pod.product',
        string='Product',
        required=True,
        ondelete='cascade',
    )
    external_id = fields.Char(
        string='External ID',
        required=True,
        help="POD provider's variant ID",
    )
    size = fields.Char(
        string='Size',
    )
    color = fields.Char(
        string='Color',
    )
    sku = fields.Char(
        string='SKU',
    )
    price = fields.Float(
        string='Price',
        help='Base price from provider',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    _sql_constraints = [
        (
            'unique_external_id_product',
            'UNIQUE(external_id, product_id)',
            'External ID must be unique per product!',
        ),
    ]

    @api.depends('size', 'color', 'sku')
    def _compute_name(self):
        """Compute name from size, color, and SKU."""
        for record in self:
            parts = []
            if record.size:
                parts.append(record.size)
            if record.color:
                parts.append(record.color)
            if record.sku:
                parts.append(f"({record.sku})")
            record.name = ' '.join(parts) if parts else record.external_id
