# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields


class PodProductCatalog(models.TransientModel):
    """Transient model for browsing POD provider product catalogs."""

    _name = 'pod.product.catalog'
    _description = 'POD Product Catalog'
    _order = 'name'

    wizard_id = fields.Many2one(
        comodel_name='pod.catalog.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='Provider',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Char(
        string='Product ID',
        help='External product ID from POD provider',
    )
    name = fields.Char(
        string='Product Name',
        help='Product name from POD provider',
    )
    description = fields.Text(
        string='Description',
        help='Product description from POD provider',
    )
    sku = fields.Char(
        string='SKU',
        help='Product SKU from POD provider',
    )
    variants = fields.Text(
        string='Variants',
        help='JSON string of available variants',
    )
    thumbnail_url = fields.Char(
        string='Thumbnail URL',
        help='Product image URL from POD provider',
    )
