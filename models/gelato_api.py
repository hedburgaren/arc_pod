# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import requests
import logging
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GelatoAPI:
    """API client for Gelato service."""

    def __init__(self, api_key):
        """
        Initialize Gelato API client.

        Args:
            api_key (str): Gelato API key
        """
        self.api_key = api_key
        self.base_url = 'https://api.gelato.com/v1'
        self.headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json',
        }
        self.timeout = 60

    def _make_request(self, method, endpoint, **kwargs):
        """
        Make HTTP request to Gelato API.

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
            _logger.error(f"Gelato API error: {str(e)}")
            raise UserError(_("Gelato API error: %s") % str(e))

    def get_products(self):
        """
        Fetch products from Gelato catalog.

        Returns:
            list: List of product dicts with keys: id, name, sku, variants

        Raises:
            UserError: If request fails
        """
        # Gelato uses /products endpoint for catalog
        endpoint = '/products'
        try:
            response = self._make_request('GET', endpoint)
            products = []
            
            # Parse Gelato response structure
            data = response.get('products', []) if isinstance(response, dict) else response
            
            for product in data:
                variants = product.get('variants', [])
                products.append({
                    'id': str(product.get('id', product.get('productUid', ''))),
                    'name': product.get('title', product.get('name', 'Unknown Product')),
                    'description': product.get('description', ''),
                    'sku': product.get('sku', ''),
                    'variants': variants,
                })
            
            _logger.info(f"Fetched {len(products)} products from Gelato")
            return products
        except Exception as e:
            _logger.error(f"Error fetching Gelato products: {str(e)}")
            raise UserError(_("Failed to fetch products from Gelato: %s") % str(e))
