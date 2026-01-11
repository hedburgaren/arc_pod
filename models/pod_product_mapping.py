# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PodProductMapping(models.Model):
    """Model for mapping Odoo products to POD provider products."""

    _name = 'pod.product.mapping'
    _description = 'POD Product Mapping'
    _order = 'odoo_product_id, provider_id'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
    )
    odoo_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Odoo Product',
        required=True,
        ondelete='cascade',
    )
    provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='POD Provider',
        required=True,
        ondelete='restrict',
    )
    pod_product_id = fields.Many2one(
        comodel_name='pod.product',
        string='POD Product',
        ondelete='restrict',
    )
    pod_variant_id = fields.Many2one(
        comodel_name='pod.product.variant',
        string='POD Variant',
        ondelete='restrict',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    last_sync = fields.Datetime(
        string='Last Sync',
        readonly=True,
        help='Last time product data was synced from POD provider',
    )

    _sql_constraints = [
        (
            'unique_odoo_product_provider',
            'UNIQUE(odoo_product_id, provider_id)',
            'Only one mapping per Odoo product and provider is allowed!',
        ),
    ]

    @api.constrains('pod_product_id', 'pod_variant_id')
    def _check_variant_belongs_to_product(self):
        """Ensure pod_variant_id belongs to the selected pod_product_id."""
        for record in self:
            if record.pod_variant_id and record.pod_product_id:
                if record.pod_variant_id.product_id != record.pod_product_id:
                    raise UserError(_(
                        "The selected variant does not belong to the selected product. "
                        "Please select a variant from the correct product."
                    ))

    @api.depends('odoo_product_id', 'pod_product_id')
    def _compute_name(self):
        """Compute display name as 'Odoo Product → POD Product'."""
        for record in self:
            odoo_name = record.odoo_product_id.name if record.odoo_product_id else 'Unknown'
            pod_name = record.pod_product_id.name if record.pod_product_id else 'Unknown'
            record.name = f"{odoo_name} → {pod_name}"

    def name_get(self):
        """Return display name as 'Odoo Product → POD Product'."""
        result = []
        for record in self:
            odoo_name = record.odoo_product_id.name if record.odoo_product_id else _('Unknown')
            pod_name = record.pod_product_id.name if record.pod_product_id else _('Unknown')
            name = f"{odoo_name} → {pod_name}"
            result.append((record.id, name))
        return result
