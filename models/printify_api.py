# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import requests
import logging
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PrintifyAPI:
    """API client for Printify service."""

    def __init__(self, api_key, shop_id=None):
        """
        Initialize Printify API client.

        Args:
            api_key (str): Printify API key
            shop_id (str): Printify shop ID
        """
        self.api_key = api_key
        self.shop_id = shop_id
        self.base_url = 'https://api.printify.com/v1'
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        self.timeout = 60

    def _make_request(self, method, endpoint, **kwargs):
        """
        Make HTTP request to Printify API.

        Args:
            method (str): HTTP method (GET, POST, etc.)
            endpoint (str): API endpoint
            **kwargs: Additional arguments for requests

        Returns:
            dict: Response data

        Raises:
            UserError: If request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        kwargs.setdefault('timeout', self.timeout)
        kwargs.setdefault('headers', self.headers)

        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            _logger.error(f"Printify API error: {str(e)}")
            raise UserError(_("Printify API error: %s") % str(e))

    def get_products(self):
        """
        Fetch products from Printify catalog.

        Returns:
            list: List of product dicts with keys: id, name, sku, variants

        Raises:
            UserError: If shop_id not configured or request fails
        """
        if not self.shop_id:
            raise UserError(_("Shop ID is required for Printify. Please configure it in Settings > ARC POD."))

        endpoint = f'/shops/{self.shop_id}/products.json'
        try:
            response = self._make_request('GET', endpoint)
            products = []
            
            # Printify returns a list of products directly
            data = response if isinstance(response, list) else response.get('data', [])
            
            for product in data:
                variants = product.get('variants', [])
                products.append({
                    'id': str(product.get('id', '')),
                    'name': product.get('title', 'Unknown Product'),
                    'description': product.get('description', ''),
                    'sku': variants[0].get('sku', '') if variants else '',
                    'variants': variants,
                })
            
            _logger.info(f"Fetched {len(products)} products from Printify")
            return products
        except Exception as e:
            _logger.error(f"Error fetching Printify products: {str(e)}")
            raise UserError(_("Failed to fetch products from Printify: %s") % str(e))
