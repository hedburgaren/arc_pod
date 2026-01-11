# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PodProvider(models.Model):
    """Model representing print-on-demand service providers."""

    _name = 'pod.provider'
    _description = 'Print on Demand Provider'
    _order = 'name'

    name = fields.Char(
        string='Provider Name',
        required=True,
        translate=True,
    )
    code = fields.Selection(
        selection=[
            ('printify', 'Printify'),
            ('gelato', 'Gelato'),
            ('printful', 'Printful'),
        ],
        string='Provider Code',
        required=True,
    )
    api_url = fields.Char(
        string='API URL',
        readonly=True,
        compute='_compute_api_url',
        store=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    logo = fields.Binary(
        string='Logo',
        attachment=True,
    )
    last_product_sync = fields.Datetime(
        string='Last Product Sync',
        readonly=True,
        help='Last time products were synced from this provider',
    )
    product_count = fields.Integer(
        string='Product Count',
        compute='_compute_product_count',
    )

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Provider code must be unique!'),
    ]

    @api.depends('code')
    def _compute_api_url(self):
        """Compute the API URL based on the provider code."""
        for record in self:
            record.api_url = record._get_api_url()

    def _get_api_url(self):
        """
        Return the correct API URL based on provider code.

        Returns:
            str: Base API URL for the provider
        """
        url_mapping = {
            'printify': 'https://api.printify.com/v1/',
            'gelato': 'https://api.gelato.com/v1/',
            'printful': 'https://api.printful.com/',
        }
        return url_mapping.get(self.code, '')

    @api.depends('code')
    def _compute_product_count(self):
        """Compute count of POD products for this provider."""
        for record in self:
            record.product_count = self.env['pod.product'].search_count([
                ('provider_id', '=', record.id)
            ])

    def action_sync_products(self):
        """Sync products from POD provider API."""
        self.ensure_one()
        
        # Get API configuration
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        api_key = IrConfigParameter.get_param('arc_pod.api_key', default='')
        shop_id = IrConfigParameter.get_param('arc_pod.shop_id', default='')
        
        if not api_key:
            raise UserError(_("API Key is not configured. Please configure it in Settings > ARC POD."))
        
        try:
            # Get the appropriate API client based on provider
            if self.code == 'printify':
                from .printify_api import PrintifyAPI
                if not shop_id:
                    raise UserError(_("Shop ID is required for Printify. Please configure it in Settings > ARC POD."))
                api_client = PrintifyAPI(api_key, shop_id)
            elif self.code == 'gelato':
                from .gelato_api import GelatoAPI
                api_client = GelatoAPI(api_key)
            elif self.code == 'printful':
                from .printful_api import PrintfulAPI
                api_client = PrintfulAPI(api_key)
            else:
                raise UserError(_("Unsupported provider: %s") % self.code)
            
            # Fetch products
            _logger.info("Fetching products from %s", self.name)
            product_data = api_client.fetch_products()
            
            if not product_data or 'products' not in product_data:
                raise UserError(_("Invalid response from provider API"))
            
            products = product_data['products']
            total_products = len(products)
            synced_count = 0
            failed_count = 0
            error_log_model = self.env['pod.error.log']
            
            for product in products:
                try:
                    # Create or update POD product
                    pod_product = self.env['pod.product'].search([
                        ('external_id', '=', product['external_id']),
                        ('provider_id', '=', self.id),
                    ], limit=1)
                    
                    product_vals = {
                        'name': product['name'],
                        'provider_id': self.id,
                        'external_id': product['external_id'],
                        'description': product.get('description', ''),
                    }
                    
                    if pod_product:
                        pod_product.write(product_vals)
                    else:
                        pod_product = self.env['pod.product'].create(product_vals)
                    
                    # Create or update variants
                    for variant_data in product.get('variants', []):
                        variant = self.env['pod.product.variant'].search([
                            ('external_id', '=', variant_data['external_id']),
                            ('product_id', '=', pod_product.id),
                        ], limit=1)
                        
                        variant_vals = {
                            'product_id': pod_product.id,
                            'external_id': variant_data['external_id'],
                            'sku': variant_data.get('sku', ''),
                            'size': variant_data.get('size', ''),
                            'color': variant_data.get('color', ''),
                            'price': variant_data.get('price', 0.0),
                        }
                        
                        if variant:
                            variant.write(variant_vals)
                        else:
                            self.env['pod.product.variant'].create(variant_vals)
                    
                    synced_count += 1
                    
                except Exception as e:
                    _logger.error(f"Error syncing product {product.get('external_id', 'unknown')}: {str(e)}")
                    failed_count += 1
                    
                    # Log error
                    error_log_model.create({
                        'provider_id': self.id,
                        'error_message': f"Failed to sync product {product.get('name', 'unknown')}: {str(e)}",
                        'error_code': 'SYNC_ERROR',
                        'request_endpoint': 'product_sync',
                    })
            
            # Update last sync time
            self.write({'last_product_sync': fields.Datetime.now()})
            
            # Show result message
            if failed_count == 0:
                message = _("Successfully synced %s products from %s") % (synced_count, self.name)
                notification_type = 'success'
            else:
                message = _("Synced %s of %s products. %s failed. Check error logs for details.") % (
                    synced_count, total_products, failed_count
                )
                notification_type = 'warning'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': notification_type,
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error syncing products from provider: {str(e)}")
            raise UserError(_("Failed to sync products: %s") % str(e))
