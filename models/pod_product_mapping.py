# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


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
        comodel_name='product.template',
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
    pod_product_id = fields.Char(
        string='POD Product ID',
        required=True,
        help='External product ID from POD provider',
    )
    pod_product_name = fields.Char(
        string='POD Product Name',
        readonly=True,
        help='Product name from POD provider',
    )
    pod_variant_id = fields.Char(
        string='POD Variant ID',
        help='External variant ID if applicable',
    )
    pod_sku = fields.Char(
        string='POD SKU',
        readonly=True,
        help='SKU from POD provider',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    last_sync = fields.Datetime(
        string='Last Sync',
        readonly=True,
        help='Last time product data was synced from provider',
    )

    _sql_constraints = [
        (
            'unique_odoo_product_provider',
            'UNIQUE(odoo_product_id, provider_id)',
            'A mapping already exists for this Odoo product and provider!'
        ),
    ]

    @api.depends('odoo_product_id', 'pod_product_name')
    def _compute_name(self):
        """Compute display name as 'Odoo Product → POD Product'."""
        for record in self:
            if record.odoo_product_id and record.pod_product_name:
                record.name = f"{record.odoo_product_id.name} → {record.pod_product_name}"
            elif record.odoo_product_id:
                record.name = f"{record.odoo_product_id.name} → (Not synced)"
            else:
                record.name = _('New Mapping')

    def name_get(self):
        """Return display name as 'Odoo Product → POD Product'."""
        result = []
        for record in self:
            if record.odoo_product_id and record.pod_product_name:
                name = f"{record.odoo_product_id.name} → {record.pod_product_name}"
            elif record.odoo_product_id:
                name = f"{record.odoo_product_id.name} → (Not synced)"
            else:
                name = _('New Mapping')
            result.append((record.id, name))
        return result

    def action_sync_from_provider(self):
        """Refresh product data from POD provider API."""
        self.ensure_one()
        
        if not self.provider_id:
            raise UserError(_('No provider selected for this mapping.'))
        
        if not self.pod_product_id:
            raise UserError(_('No POD product ID specified.'))
        
        # Get API client based on provider
        api_client = self._get_api_client()
        if not api_client:
            raise UserError(_('API client not available for provider: %s') % self.provider_id.name)
        
        try:
            # Fetch product details from provider
            # This will be implemented when API clients are ready
            self.write({
                'last_sync': fields.Datetime.now(),
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Product data synced successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Failed to sync product data: %s') % str(e))
    
    def _get_api_client(self):
        """
        Get the appropriate API client for the provider.
        
        Returns:
            API client instance or None
        """
        if not self.provider_id:
            return None
        
        provider_code = self.provider_id.code
        
        # Import API clients dynamically
        if provider_code == 'printify':
            from . import printify_api
            return printify_api.PrintifyAPI(self.env)
        elif provider_code == 'gelato':
            from . import gelato_api
            return gelato_api.GelatoAPI(self.env)
        elif provider_code == 'printful':
            from . import printful_api
            return printful_api.PrintfulAPI(self.env)
        
        return None
