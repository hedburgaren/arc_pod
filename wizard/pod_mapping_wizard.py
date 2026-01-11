# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PodMappingWizard(models.TransientModel):
    """Wizard for quick product mapping creation."""

    _name = 'pod.mapping.wizard'
    _description = 'POD Mapping Wizard'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Odoo Product',
        required=True,
    )
    provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='POD Provider',
        required=True,
    )
    pod_product_id = fields.Many2one(
        comodel_name='pod.product',
        string='POD Product',
        domain="[('provider_id', '=', provider_id)]",
    )
    pod_variant_id = fields.Many2one(
        comodel_name='pod.product.variant',
        string='POD Variant',
        domain="[('product_id', '=', pod_product_id)]",
    )

    def action_create_mapping(self):
        """Create POD product mapping and close wizard."""
        self.ensure_one()

        # Check if mapping already exists
        existing_mapping = self.env['pod.product.mapping'].search([
            ('odoo_product_id', '=', self.product_id.id),
            ('provider_id', '=', self.provider_id.id),
        ], limit=1)

        if existing_mapping:
            raise UserError(_(
                "A mapping already exists for this product and provider. "
                "Please edit the existing mapping instead."
            ))

        # Create mapping
        mapping_vals = {
            'odoo_product_id': self.product_id.id,
            'provider_id': self.provider_id.id,
            'pod_product_id': self.pod_product_id.id if self.pod_product_id else False,
            'pod_variant_id': self.pod_variant_id.id if self.pod_variant_id else False,
        }

        mapping = self.env['pod.product.mapping'].create(mapping_vals)

        # Show success notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Product mapping created successfully'),
                'type': 'success',
                'sticky': False,
            }
        }
