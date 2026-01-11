# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json
from odoo import models, fields


class PodProductCatalog(models.TransientModel):
    """Transient model for browsing POD provider product catalogs."""

    _name = 'pod.product.catalog'
    _description = 'POD Product Catalog'

    provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='Provider',
        required=True,
    )
    product_id = fields.Char(
        string='Product ID',
        help='External product ID from POD provider',
    )
    name = fields.Char(
        string='Product Name',
    )
    description = fields.Text(
        string='Description',
    )
    sku = fields.Char(
        string='SKU',
    )
    variants = fields.Text(
        string='Variants',
        help='JSON string of available variants',
    )
    thumbnail_url = fields.Char(
        string='Thumbnail URL',
    )
