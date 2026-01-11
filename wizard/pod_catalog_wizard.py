# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PodCatalogWizard(models.TransientModel):
    """Wizard for browsing POD provider catalog and creating product mappings."""

    _name = 'pod.catalog.wizard'
    _description = 'POD Catalog Wizard'

    provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='Provider',
        required=True,
        help='Select the POD provider to fetch products from',
    )
    catalog_ids = fields.One2many(
        comodel_name='pod.product.catalog',
        inverse_name='wizard_id',
        string='Available Products',
        help='Products available from the selected provider',
    )
    selected_catalog_id = fields.Many2one(
        comodel_name='pod.product.catalog',
        string='Selected Product',
        help='Selected product to map',
    )
    odoo_product_id = fields.Many2one(
        comodel_name='product.template',
        string='Odoo Product',
        required=True,
        help='Odoo product to map to POD provider product',
    )

    def action_fetch_catalog(self):
        """
        Fetch products from selected provider.
        
        Steps:
        1. Get API client for selected provider
        2. Call get_products()
        3. Populate catalog_ids with results
        4. Refresh view
        """
        self.ensure_one()
        
        if not self.provider_id:
            raise ValidationError(_('Please select a provider first.'))
        
        # Check if provider is configured
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        selected_provider_id = IrConfigParameter.get_param('arc_pod.selected_provider_id', default=False)
        
        if not selected_provider_id or int(selected_provider_id) != self.provider_id.id:
            raise UserError(
                _('The selected provider is not configured in Settings > ARC POD. '
                  'Please configure it first.')
            )
        
        # Get API client based on provider
        api_client = self._get_api_client()
        if not api_client:
            raise UserError(_('API client not available for provider: %s') % self.provider_id.name)
        
        try:
            # Fetch products from API
            products = api_client.get_products()
            
            # Clear existing catalog entries
            self.catalog_ids.unlink()
            
            # Create catalog entries
            catalog_vals = []
            for product in products:
                # Store variants as JSON string
                variants_json = json.dumps(product.get('variants', []))
                
                catalog_vals.append({
                    'wizard_id': self.id,
                    'provider_id': self.provider_id.id,
                    'product_id': product.get('id', ''),
                    'name': product.get('name', ''),
                    'description': product.get('description', ''),
                    'sku': product.get('sku', ''),
                    'variants': variants_json,
                    'thumbnail_url': product.get('thumbnail_url', ''),
                })
            
            if catalog_vals:
                self.env['pod.product.catalog'].create(catalog_vals)
            else:
                raise UserError(_('No products found for this provider. Please check your configuration.'))
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Successfully fetched %d products from %s') % (len(catalog_vals), self.provider_id.name),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except UserError:
            raise
        except Exception as e:
            _logger.error(f"Failed to fetch catalog: {str(e)}")
            raise UserError(_('Failed to fetch products: %s') % str(e))

    def action_create_mapping(self):
        """
        Create product mapping from selected catalog item.
        
        Steps:
        1. Validate selection
        2. Create pod.product.mapping record
        3. Close wizard
        """
        self.ensure_one()
        
        if not self.selected_catalog_id:
            raise ValidationError(_('Please select a product from the catalog first.'))
        
        if not self.odoo_product_id:
            raise ValidationError(_('Odoo product is required.'))
        
        # Check if mapping already exists
        existing_mapping = self.env['pod.product.mapping'].search([
            ('odoo_product_id', '=', self.odoo_product_id.id),
            ('provider_id', '=', self.provider_id.id),
        ])
        
        if existing_mapping:
            raise ValidationError(
                _('A mapping already exists for this product and provider. '
                  'Please edit the existing mapping instead.')
            )
        
        # Create mapping
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
            from odoo.addons.arc_pod.models.printify_api import PrintifyAPI
            return PrintifyAPI(self.env)
        elif provider_code == 'gelato':
            from odoo.addons.arc_pod.models.gelato_api import GelatoAPI
            return GelatoAPI(self.env)
        elif provider_code == 'printful':
            from odoo.addons.arc_pod.models.printful_api import PrintfulAPI
            return PrintfulAPI(self.env)
        
        return None
