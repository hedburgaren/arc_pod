# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from odoo import _
from .pod_api_client import PodAPIClient

_logger = logging.getLogger(__name__)


class PrintfulAPI(PodAPIClient):
    """API client for Printful integration."""

    def __init__(self, api_key, base_url='https://api.printful.com/'):
        """
        Initialize Printful API client.

        Args:
            api_key (str): Printful API key
            base_url (str): Base URL for Printful API
        """
        super().__init__(api_key=api_key, base_url=base_url)

    def _get_headers(self):
        """
        Get authentication headers for Printful API.

        Returns:
            dict: Headers with Bearer token authentication
        """
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def test_connection(self):
        """
        Test connection to Printful API.
        Calls GET /stores endpoint.

        Returns:
            dict: {'success': bool, 'message': str}
        """
        _logger.info("Testing Printful API connection")

        success, response_data, status_code, error_message = self._make_request(
            endpoint='stores',
            method='GET'
        )

        if success:
            message = _("Connection successful: Printful API is accessible")
            _logger.info(message)
            return {'success': True, 'message': message}
        else:
            _logger.error("Printful connection test failed: %s", error_message)
            return {'success': False, 'message': error_message}

    def get_products(self):
        """
        Get products from Printful catalog.
        Calls GET /products endpoint.

        Returns:
            list: List of product dictionaries with structure:
                [{'id': '...', 'name': '...', 'sku': '...', 'variants': [...]}]
        """
        _logger.info("Fetching products from Printful")

        # Set longer timeout for catalog requests
        original_timeout = self.timeout
        self.timeout = 60

        try:
            success, response_data, status_code, error_message = self._make_request(
                endpoint='products',
                method='GET'
            )

            if success and response_data:
                # Parse Printful response
                products = []
                # Printful wraps data in a 'result' key
                product_list = response_data.get('result', []) if isinstance(response_data, dict) else response_data

                for item in product_list:
                    product = {
                        'id': str(item.get('id', '')),
                        'name': item.get('name', item.get('title', '')),
                        'sku': item.get('sku', ''),
                        'variants': item.get('variants', []),
                        'description': item.get('description', ''),
                        'thumbnail_url': item.get('image', item.get('thumbnail_url', '')),
                    }
                    products.append(product)

                _logger.info("Successfully fetched %d products from Printful", len(products))
                return products
            else:
                _logger.error("Failed to fetch products from Printful: %s", error_message)
                return []
        finally:
            # Restore original timeout
            self.timeout = original_timeout
