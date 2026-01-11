# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from odoo import _
from .pod_api_client import PodAPIClient

_logger = logging.getLogger(__name__)


class PrintifyAPI(PodAPIClient):
    """API client for Printify integration."""

    def __init__(self, api_key, base_url='https://api.printify.com/v1/'):
        """
        Initialize Printify API client.

        Args:
            api_key (str): Printify API key
            base_url (str): Base URL for Printify API
        """
        super().__init__(api_key=api_key, base_url=base_url)

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

    def get_products(self, shop_id=None):
        """
        Get products from Printify.
        Calls GET /v1/shops/{shop_id}/products.json endpoint.

        Args:
            shop_id (str): Shop ID (required for Printify)

        Returns:
            list: List of product dictionaries with structure:
                [{'id': '...', 'name': '...', 'sku': '...', 'variants': [...]}]
        """
        if not shop_id:
            _logger.error("Shop ID is required for Printify get_products")
            return []

        _logger.info("Fetching products from Printify shop %s", shop_id)

        # Set longer timeout for catalog requests
        original_timeout = self.timeout
        self.timeout = 60

        try:
            success, response_data, status_code, error_message = self._make_request(
                endpoint=f'shops/{shop_id}/products.json',
                method='GET'
            )

            if success and response_data:
                # Parse Printify response
                products = []
                product_list = response_data.get('data', []) if isinstance(response_data, dict) else response_data

                for item in product_list:
                    product = {
                        'id': str(item.get('id', '')),
                        'name': item.get('title', ''),
                        'sku': '',  # Printify doesn't have a single SKU, it's per variant
                        'variants': item.get('variants', []),
                        'description': item.get('description', ''),
                        'thumbnail_url': item.get('images', [{}])[0].get('src', '') if item.get('images') else '',
                    }
                    products.append(product)

                _logger.info("Successfully fetched %d products from Printify", len(products))
                return products
            else:
                _logger.error("Failed to fetch products from Printify: %s", error_message)
                return []
        finally:
            # Restore original timeout
            self.timeout = original_timeout
