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
        help='Last time product data was synced from POD provider',
    )

    _sql_constraints = [
        (
            'unique_odoo_product_provider',
            'UNIQUE(odoo_product_id, provider_id)',
            'Only one mapping per Odoo product and provider is allowed!',
        ),
    ]

    @api.depends('odoo_product_id', 'pod_product_name')
    def _compute_name(self):
        """Compute display name as 'Odoo Product → POD Product'."""
        for record in self:
            odoo_name = record.odoo_product_id.name if record.odoo_product_id else 'Unknown'
            pod_name = record.pod_product_name or 'Unknown'
            record.name = f"{odoo_name} → {pod_name}"

    def name_get(self):
        """Return display name as 'Odoo Product → POD Product'."""
        result = []
        for record in self:
            odoo_name = record.odoo_product_id.name if record.odoo_product_id else _('Unknown')
            pod_name = record.pod_product_name or _('Unknown')
            name = f"{odoo_name} → {pod_name}"
            result.append((record.id, name))
        return result

    def action_sync_from_provider(self):
        """Refresh product data from POD provider API."""
        self.ensure_one()
        
        # Get API configuration
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        api_key = IrConfigParameter.get_param('arc_pod.api_key', default='')
        shop_id = IrConfigParameter.get_param('arc_pod.shop_id', default='')
        
        if not api_key:
            raise UserError(_("API Key is not configured. Please configure it in Settings > ARC POD."))
        
        try:
            # Get the appropriate API client based on provider
            provider_code = self.provider_id.code
            
            if provider_code == 'printify':
                from .printify_api import PrintifyAPI
                if not shop_id:
                    raise UserError(_("Shop ID is required for Printify. Please configure it in Settings > ARC POD."))
                api_client = PrintifyAPI(api_key, shop_id)
            elif provider_code == 'gelato':
                from .gelato_api import GelatoAPI
                api_client = GelatoAPI(api_key)
            elif provider_code == 'printful':
                from .printful_api import PrintfulAPI
                api_client = PrintfulAPI(api_key)
            else:
                raise UserError(_("Unsupported provider: %s") % provider_code)
            
            # Fetch products and find the matching one
            products = api_client.get_products()
            matching_product = None
            
            for product in products:
                if product['id'] == self.pod_product_id:
                    matching_product = product
                    break
            
            if matching_product:
                # Update mapping with fresh data
                self.write({
                    'pod_product_name': matching_product['name'],
                    'pod_sku': matching_product['sku'],
                    'last_sync': fields.Datetime.now(),
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('Product data refreshed successfully from %s') % self.provider_id.name,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_("Product %s not found in %s catalog") % (self.pod_product_id, self.provider_id.name))
                
        except Exception as e:
            _logger.error(f"Error syncing product from provider: {str(e)}")
            raise UserError(_("Failed to sync product: %s") % str(e))
