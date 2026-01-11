# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from odoo import _
from .pod_api_client import PodAPIClient

_logger = logging.getLogger(__name__)


class PrintifyAPI(PodAPIClient):
    """API client for Printify integration."""

    def __init__(self, api_key, shop_id=None, base_url='https://api.printify.com/v1/'):
        """
        Initialize Printify API client.

        Args:
            api_key (str): Printify API key
            shop_id (str): Printify shop ID
            base_url (str): Base URL for Printify API
        """
        super().__init__(api_key=api_key, base_url=base_url)
        self.shop_id = shop_id

    def _get_headers(self):
        """
        Get authentication headers for Printify API.

        Returns:
            dict: Headers with Bearer token authentication
        """
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def test_connection(self):
        """
        Test connection to Printify API.
        Calls GET /v1/shops.json endpoint.

        Returns:
            dict: {'success': bool, 'message': str}
        """
        _logger.info("Testing Printify API connection")

        success, response_data, status_code, error_message = self._make_request(
            endpoint='shops.json',
            method='GET'
        )

        if success:
            message = _("Connection successful: Printify API is accessible")
            _logger.info(message)
            return {'success': True, 'message': message}
        else:
            _logger.error("Printify connection test failed: %s", error_message)
            return {'success': False, 'message': error_message}

    def fetch_products(self):
        """
        Fetch products from Printify API.
        Calls GET /v1/shops/{shop_id}/products.json endpoint.

        Returns:
            dict: Standardized product data with format:
                {
                    'products': [
                        {
                            'external_id': 'product_id',
                            'name': 'Product Name',
                            'description': 'Description',
                            'variants': [
                                {
                                    'external_id': 'variant_id',
                                    'sku': 'SKU123',
                                    'size': 'M',
                                    'color': 'Blue',
                                    'price': 25.99
                                }
                            ]
                        }
                    ]
                }
        """
        _logger.info("Fetching products from Printify API")

        # Get shop_id from the base_url or API key context
        # For now, we'll need to extract it from initialization
        shop_id = getattr(self, 'shop_id', None)
        if not shop_id:
            _logger.error("Shop ID not provided for Printify API")
            return {'products': []}

        success, response_data, status_code, error_message = self._make_request(
            endpoint=f'shops/{shop_id}/products.json',
            method='GET'
        )

        if not success:
            _logger.error("Failed to fetch Printify products: %s", error_message)
            return {'products': []}

        # Parse Printify response to standardized format
        products = []
        for item in response_data.get('data', []):
            product = {
                'external_id': str(item.get('id', '')),
                'name': item.get('title', ''),
                'description': item.get('description', ''),
                'variants': []
            }

            # Parse variants
            for variant in item.get('variants', []):
                product['variants'].append({
                    'external_id': str(variant.get('id', '')),
                    'sku': variant.get('sku', ''),
                    'size': '',  # Printify doesn't have standard size field
                    'color': '',  # Printify doesn't have standard color field
                    'price': float(variant.get('price', 0)) / 100,  # Printify uses cents
                })

            products.append(product)

        _logger.info("Fetched %s products from Printify", len(products))
        return {'products': products}
