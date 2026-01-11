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

    def create_order(self, order_data):
        """
        Create an order in Printify.
        Calls POST /v1/shops/{shop_id}/orders.json endpoint.

        Args:
            order_data (dict): Order data in format:
                {
                    'external_id': 'SO001-12345',
                    'line_items': [
                        {
                            'product_id': '5d39a59...',
                            'variant_id': '12345',
                            'quantity': 2
                        }
                    ],
                    'shipping_method': 1,
                    'address_to': {
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'email': 'john@example.com',
                        'address1': '123 Main St',
                        'city': 'New York',
                        'zip': '10001',
                        'country': 'US'
                    }
                }

        Returns:
            dict: {'success': True/False, 'order_id': '...', 'message': '...'}
        """
        _logger.info("Creating order in Printify")

        shop_id = getattr(self, 'shop_id', None)
        if not shop_id:
            _logger.error("Shop ID not provided for Printify API")
            return {
                'success': False,
                'message': _("Shop ID not configured for Printify"),
            }

        success, response_data, status_code, error_message = self._make_request(
            endpoint=f'shops/{shop_id}/orders.json',
            method='POST',
            data=order_data
        )

        if success:
            order_id = response_data.get('id', '')
            _logger.info("Order created successfully in Printify: %s", order_id)
            return {
                'success': True,
                'order_id': str(order_id),
                'message': _("Order created successfully"),
            }
        else:
            _logger.error("Failed to create Printify order: %s", error_message)
            return {
                'success': False,
                'message': error_message,
            }

    def get_order_status(self, order_id):
        """
        Get order status from Printify.
        Calls GET /v1/shops/{shop_id}/orders/{order_id}.json endpoint.

        Args:
            order_id (str): Printify order ID

        Returns:
            dict: {
                'tracking_number': '...',
                'tracking_url': '...',
                'status': '...'
            }
        """
        _logger.info("Fetching order status from Printify: %s", order_id)

        shop_id = getattr(self, 'shop_id', None)
        if not shop_id:
            _logger.error("Shop ID not provided for Printify API")
            return {}

        success, response_data, status_code, error_message = self._make_request(
            endpoint=f'shops/{shop_id}/orders/{order_id}.json',
            method='GET'
        )

        if success:
            # Extract tracking information
            shipments = response_data.get('shipments', [])
            tracking_number = ''
            tracking_url = ''
            
            if shipments:
                tracking_number = shipments[0].get('tracking_number', '')
                tracking_url = shipments[0].get('tracking_url', '')
            
            status = response_data.get('status', '')
            
            _logger.info("Order status fetched: %s", status)
            return {
                'tracking_number': tracking_number,
                'tracking_url': tracking_url,
                'status': status,
            }
        else:
            _logger.error("Failed to fetch Printify order status: %s", error_message)
            return {}
