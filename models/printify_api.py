# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import requests
import logging
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PrintifyAPI:
    """API client for Printify integration."""

    def __init__(self, env):
        """
        Initialize Printify API client.
        
        Args:
            env: Odoo environment
        """
        self.env = env
        self.base_url = 'https://api.printify.com/v1/'
        self.timeout = 60
        self._load_config()

    def _load_config(self):
        """Load configuration from system parameters."""
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        self.api_key = IrConfigParameter.get_param('arc_pod.api_key', default='')
        self.shop_id = IrConfigParameter.get_param('arc_pod.shop_id', default='')
        
        if not self.api_key:
            raise UserError(_('Printify API key not configured. Please configure it in Settings > ARC POD.'))
        
        if not self.shop_id:
            raise UserError(_('Printify Shop ID not configured. Please configure it in Settings > ARC POD.'))

    def _get_headers(self):
        """
        Get HTTP headers for API requests.
        
        Returns:
            dict: HTTP headers
        """
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def _make_request(self, method, endpoint, **kwargs):
        """
        Make HTTP request to Printify API.
        
        Args:
            method (str): HTTP method (GET, POST, etc.)
            endpoint (str): API endpoint
            **kwargs: Additional arguments for requests
            
        Returns:
            dict: API response
            
        Raises:
            UserError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            _logger.error(f"Printify API timeout for {endpoint}")
            raise UserError(_('Request to Printify API timed out. Please try again.'))
        except requests.exceptions.RequestException as e:
            _logger.error(f"Printify API error for {endpoint}: {str(e)}")
            raise UserError(_('Failed to communicate with Printify API: %s') % str(e))

    def get_products(self):
        """
        Fetch products from Printify shop.
        
        Returns:
            list: List of product dictionaries with standardized structure
                [{'id': '...', 'name': '...', 'sku': '...', 'variants': [...]}]
        """
        endpoint = f"shops/{self.shop_id}/products.json"
        
        try:
            response = self._make_request('GET', endpoint)
            
            # Parse response to uniform structure
            products = []
            data = response.get('data', []) if isinstance(response, dict) else response
            
            for item in data:
                product = {
                    'id': str(item.get('id', '')),
                    'name': item.get('title', ''),
                    'description': item.get('description', ''),
                    'sku': '',  # Printify doesn't have a direct SKU field at product level
                    'variants': item.get('variants', []),
                    'thumbnail_url': '',
                }
                
                # Extract thumbnail from images if available
                images = item.get('images', [])
                if images and len(images) > 0:
                    product['thumbnail_url'] = images[0].get('src', '')
                
                products.append(product)
            
            _logger.info(f"Fetched {len(products)} products from Printify")
            return products
            
        except Exception as e:
            _logger.error(f"Failed to fetch Printify products: {str(e)}")
            # Log error to pod.error.log if model exists
            try:
                self.env['pod.error.log'].create({
                    'provider_id': self.env.ref('arc_pod.pod_provider_printify').id,
                    'error_type': 'api_error',
                    'error_message': str(e),
                })
            except:
                pass  # Error log model might not exist yet
            raise
