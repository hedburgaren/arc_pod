# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from odoo import _
from .pod_api_client import PodAPIClient

_logger = logging.getLogger(__name__)


class GelatoAPI(PodAPIClient):
    """API client for Gelato integration."""

    def __init__(self, api_key, base_url='https://api.gelato.com/v1/'):
        """
        Initialize Gelato API client.

        Args:
            api_key (str): Gelato API key
            base_url (str): Base URL for Gelato API
        """
        super().__init__(api_key=api_key, base_url=base_url)

    def _get_headers(self):
        """
        Get authentication headers for Gelato API.

        Returns:
            dict: Headers with X-API-KEY authentication
        """
        return {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json',
        }

    def test_connection(self):
        """
        Test connection to Gelato API.
        Calls GET /v1/ping endpoint.

        Returns:
            dict: {'success': bool, 'message': str}
        """
        _logger.info("Testing Gelato API connection")

        success, response_data, status_code, error_message = self._make_request(
            endpoint='ping',
            method='GET'
        )

        if success:
            message = _("Connection successful: Gelato API is accessible")
            _logger.info(message)
            return {'success': True, 'message': message}
        else:
            _logger.error("Gelato connection test failed: %s", error_message)
            return {'success': False, 'message': error_message}

    def get_products(self):
        """
        Get products from Gelato product catalog.
        Calls GET /v1/products endpoint.

        Returns:
            list: List of product dictionaries with structure:
                [{'id': '...', 'name': '...', 'sku': '...', 'variants': [...]}]
        """
        _logger.info("Fetching products from Gelato")

        # Set longer timeout for catalog requests
        original_timeout = self.timeout
        self.timeout = 60

        try:
            success, response_data, status_code, error_message = self._make_request(
                endpoint='products',
                method='GET'
            )

            if success and response_data:
                # Parse Gelato response
                products = []
                product_list = response_data.get('products', []) if isinstance(response_data, dict) else response_data

                for item in product_list:
                    product = {
                        'id': str(item.get('uid', item.get('id', ''))),
                        'name': item.get('name', item.get('title', '')),
                        'sku': item.get('sku', ''),
                        'variants': item.get('variants', []),
                        'description': item.get('description', ''),
                        'thumbnail_url': item.get('previewUrl', item.get('image', '')),
                    }
                    products.append(product)

                _logger.info("Successfully fetched %d products from Gelato", len(products))
                return products
            else:
                _logger.error("Failed to fetch products from Gelato: %s", error_message)
                return []
        finally:
            # Restore original timeout
            self.timeout = original_timeout
