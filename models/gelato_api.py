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

    def fetch_products(self):
        """
        Fetch products from Gelato API.
        Calls appropriate Gelato endpoint for product catalog.

        Returns:
            dict: Standardized product data
        """
        _logger.info("Fetching products from Gelato API")

        success, response_data, status_code, error_message = self._make_request(
            endpoint='products',
            method='GET'
        )

        if not success:
            _logger.error("Failed to fetch Gelato products: %s", error_message)
            return {'products': []}

        # Parse Gelato response to standardized format
        products = []
        for item in response_data.get('products', []):
            product = {
                'external_id': str(item.get('uid', '')),
                'name': item.get('title', ''),
                'description': item.get('description', ''),
                'variants': []
            }

            # Parse variants
            for variant in item.get('variants', []):
                product['variants'].append({
                    'external_id': str(variant.get('uid', '')),
                    'sku': variant.get('sku', ''),
                    'size': variant.get('size', ''),
                    'color': variant.get('color', ''),
                    'price': float(variant.get('price', {}).get('amount', 0)),
                })

            products.append(product)

        _logger.info("Fetched %s products from Gelato", len(products))
        return {'products': products}

    def create_order(self, order_data):
        """
        Create an order in Gelato.
        Calls appropriate Gelato order creation endpoint.

        Args:
            order_data (dict): Order data in Gelato format

        Returns:
            dict: {'success': True/False, 'order_id': '...', 'message': '...'}
        """
        _logger.info("Creating order in Gelato")

        success, response_data, status_code, error_message = self._make_request(
            endpoint='orders',
            method='POST',
            data=order_data
        )

        if success:
            order_id = response_data.get('orderUid', '')
            _logger.info("Order created successfully in Gelato: %s", order_id)
            return {
                'success': True,
                'order_id': str(order_id),
                'message': _("Order created successfully"),
            }
        else:
            _logger.error("Failed to create Gelato order: %s", error_message)
            return {
                'success': False,
                'message': error_message,
            }

    def get_order_status(self, order_id):
        """
        Get order status from Gelato.
        Calls appropriate Gelato status endpoint.

        Args:
            order_id (str): Gelato order ID

        Returns:
            dict: {
                'tracking_number': '...',
                'tracking_url': '...',
                'status': '...'
            }
        """
        _logger.info("Fetching order status from Gelato: %s", order_id)

        success, response_data, status_code, error_message = self._make_request(
            endpoint=f'orders/{order_id}',
            method='GET'
        )

        if success:
            # Extract tracking information
            tracking_number = response_data.get('trackingNumber', '')
            tracking_url = response_data.get('trackingUrl', '')
            status = response_data.get('status', '')
            
            _logger.info("Order status fetched: %s", status)
            return {
                'tracking_number': tracking_number,
                'tracking_url': tracking_url,
                'status': status,
            }
        else:
            _logger.error("Failed to fetch Gelato order status: %s", error_message)
            return {}
