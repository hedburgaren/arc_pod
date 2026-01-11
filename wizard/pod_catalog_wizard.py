# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PodCatalogWizard(models.TransientModel):
    """Wizard for browsing POD product catalogs and creating mappings."""

    _name = 'pod.catalog.wizard'
    _description = 'POD Catalog Wizard'

    provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='Provider',
        required=True,
    )
    odoo_product_id = fields.Many2one(
        comodel_name='product.template',
        string='Odoo Product',
        required=True,
    )
    catalog_ids = fields.One2many(
        comodel_name='pod.product.catalog',
        inverse_name='create_uid',  # Using create_uid as a workaround for transient models
        string='Available Products',
    )
    selected_catalog_id = fields.Many2one(
        comodel_name='pod.product.catalog',
        string='Selected Product',
        help='Selected product from catalog',
    )

    def action_fetch_catalog(self):
        """Fetch products from selected provider and populate catalog."""
        self.ensure_one()
        
        if not self.provider_id:
            raise UserError(_("Please select a provider first."))
        
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
                from ..models.printify_api import PrintifyAPI
                if not shop_id:
                    raise UserError(_("Shop ID is required for Printify. Please configure it in Settings > ARC POD."))
                api_client = PrintifyAPI(api_key, shop_id)
            elif provider_code == 'gelato':
                from ..models.gelato_api import GelatoAPI
                api_client = GelatoAPI(api_key)
            elif provider_code == 'printful':
                from ..models.printful_api import PrintfulAPI
                api_client = PrintfulAPI(api_key)
            else:
                raise UserError(_("Unsupported provider: %s") % provider_code)
            
            # Fetch products
            products = api_client.get_products()
            
            if not products:
                raise UserError(_("No products found in %s catalog.") % self.provider_id.name)
            
            # Clear existing catalog entries
            self.catalog_ids.unlink()
            
            # Create catalog entries
            CatalogModel = self.env['pod.product.catalog']
            for product in products:
                CatalogModel.create({
                    'provider_id': self.provider_id.id,
                    'product_id': product['id'],
                    'name': product['name'],
                    'description': product.get('description', ''),
                    'sku': product.get('sku', ''),
                    'variants': json.dumps(product.get('variants', [])),
                })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Fetched %s products from %s') % (len(products), self.provider_id.name),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error fetching catalog: {str(e)}")
            raise UserError(_("Failed to fetch catalog: %s") % str(e))

    def action_create_mapping(self):
        """Create product mapping from selected catalog item."""
        self.ensure_one()
        
        if not self.selected_catalog_id:
            raise UserError(_("Please select a product from the catalog first."))
        
        # Check if mapping already exists
        existing_mapping = self.env['pod.product.mapping'].search([
            ('odoo_product_id', '=', self.odoo_product_id.id),
            ('provider_id', '=', self.provider_id.id),
        ])
        
        if existing_mapping:
            raise UserError(_(
                "A mapping already exists for this product and provider. "
                "Please edit the existing mapping or delete it first."
            ))
        
        # Create the mapping
        mapping_vals = {
            'odoo_product_id': self.odoo_product_id.id,
            'provider_id': self.provider_id.id,
            'pod_product_id': self.selected_catalog_id.product_id,
            'pod_product_name': self.selected_catalog_id.name,
            'pod_sku': self.selected_catalog_id.sku,
            'last_sync': fields.Datetime.now(),
        }
        
        mapping = self.env['pod.product.mapping'].create(mapping_vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Product mapping created successfully!'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
