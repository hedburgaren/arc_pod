# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import requests
import logging
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PrintfulAPI:
    """API client for Printful integration."""

    def __init__(self, env):
        """
        Initialize Printful API client.
        
        Args:
            env: Odoo environment
        """
        self.env = env
        self.base_url = 'https://api.printful.com/'
        self.timeout = 60
        self._load_config()

    def _load_config(self):
        """Load configuration from system parameters."""
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        self.api_key = IrConfigParameter.get_param('arc_pod.api_key', default='')
        
        if not self.api_key:
            raise UserError(_('Printful API key not configured. Please configure it in Settings > ARC POD.'))

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
        Make HTTP request to Printful API.
        
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
            _logger.error(f"Printful API timeout for {endpoint}")
            raise UserError(_('Request to Printful API timed out. Please try again.'))
        except requests.exceptions.RequestException as e:
            _logger.error(f"Printful API error for {endpoint}: {str(e)}")
            raise UserError(_('Failed to communicate with Printful API: %s') % str(e))

    def get_products(self):
        """
        Fetch products from Printful catalog.
        
        Returns:
            list: List of product dictionaries with standardized structure
                [{'id': '...', 'name': '...', 'sku': '...', 'variants': [...]}]
        """
        endpoint = "products"
        
        try:
            response = self._make_request('GET', endpoint)
            
            # Parse response to uniform structure
            products = []
            # Printful wraps response in 'result' field
            data = response.get('result', []) if isinstance(response, dict) else response
            
            for item in data:
                product = {
                    'id': str(item.get('id', '')),
                    'name': item.get('name', '') or item.get('title', ''),
                    'description': item.get('description', ''),
                    'sku': '',  # Printful provides SKU at variant level
                    'variants': item.get('variants', []),
                    'thumbnail_url': item.get('thumbnail_url', '') or item.get('image', ''),
                }
                
                products.append(product)
            
            _logger.info(f"Fetched {len(products)} products from Printful")
            return products
            
        except Exception as e:
            _logger.error(f"Failed to fetch Printful products: {str(e)}")
            # Log error to pod.error.log if model exists
            try:
                self.env['pod.error.log'].create({
                    'provider_id': self.env.ref('arc_pod.pod_provider_printful').id,
                    'error_type': 'api_error',
                    'error_message': str(e),
                })
            except:
                pass  # Error log model might not exist yet
            raise
