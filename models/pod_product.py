# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields, api


class PodProduct(models.Model):
    """Model representing POD provider products."""

    _name = 'pod.product'
    _description = 'POD Product'
    _order = 'name'

    name = fields.Char(
        string='Product Name',
        required=True,
        help='Product name from POD provider',
    )
    provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='Provider',
        required=True,
        ondelete='cascade',
    )
    external_id = fields.Char(
        string='External ID',
        required=True,
        help="POD provider's product ID",
    )
    description = fields.Text(
        string='Description',
    )
    image = fields.Binary(
        string='Image',
        attachment=True,
    )
    variant_ids = fields.One2many(
        comodel_name='pod.product.variant',
        inverse_name='product_id',
        string='Variants',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    _sql_constraints = [
        (
            'unique_external_id_provider',
            'UNIQUE(external_id, provider_id)',
            'External ID must be unique per provider!',
        ),
    ]
