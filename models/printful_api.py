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

    def fetch_products(self):
        """
        Fetch products from Printful API.
        Calls GET /products endpoint.

        Returns:
            dict: Standardized product data
        """
        _logger.info("Fetching products from Printful API")

        success, response_data, status_code, error_message = self._make_request(
            endpoint='products',
            method='GET'
        )

        if not success:
            _logger.error("Failed to fetch Printful products: %s", error_message)
            return {'products': []}

        # Parse Printful response to standardized format
        products = []
        for item in response_data.get('result', []):
            product = {
                'external_id': str(item.get('id', '')),
                'name': item.get('name', ''),
                'description': item.get('description', ''),
                'variants': []
            }

            # Parse variants
            for variant in item.get('variants', []):
                product['variants'].append({
                    'external_id': str(variant.get('id', '')),
                    'sku': variant.get('sku', ''),
                    'size': variant.get('size', ''),
                    'color': variant.get('color', ''),
                    'price': float(variant.get('price', 0)),
                })

            products.append(product)

        _logger.info("Fetched %s products from Printful", len(products))
        return {'products': products}

    def create_order(self, order_data):
        """
        Create a new order in Printful.
        Calls POST /orders endpoint.

        Args:
            order_data (dict): Order data with recipient and items

        Returns:
            dict: {'success': bool, 'order_id': str, 'message': str}
        """
        _logger.info("Creating order in Printful")

        # Transform order data to Printful format
        printful_data = {
            'external_id': order_data.get('external_id', ''),
            'recipient': {
                'name': order_data['recipient'].get('name', ''),
                'address1': order_data['recipient'].get('address1', ''),
                'address2': order_data['recipient'].get('address2', ''),
                'city': order_data['recipient'].get('city', ''),
                'state_code': order_data['recipient'].get('state', ''),
                'country_code': order_data['recipient'].get('country', ''),
                'zip': order_data['recipient'].get('zip', ''),
                'email': order_data['recipient'].get('email', ''),
                'phone': order_data['recipient'].get('phone', ''),
            },
            'items': []
        }

        # Add order items
        for item in order_data.get('items', []):
            printful_item = {
                'variant_id': item.get('variant_id', item.get('product_id')),
                'quantity': item.get('quantity', 1),
            }
            
            # Add product_id if variant_id is different
            if item.get('product_id'):
                printful_item['sync_variant_id'] = item['product_id']
            
            printful_data['items'].append(printful_item)

        success, response_data, status_code, error_message = self._make_request(
            endpoint='orders',
            method='POST',
            data=printful_data
        )

        if success:
            result = response_data.get('result', {})
            order_id = result.get('id', '')
            _logger.info("Order created successfully in Printful: %s", order_id)
            return {
                'success': True,
                'order_id': str(order_id),
                'message': _("Order created successfully")
            }
        else:
            _logger.error("Failed to create order in Printful: %s", error_message)
            return {
                'success': False,
                'message': error_message
            }

    def get_order_status(self, order_id):
        """
        Get order status from Printful.
        Calls GET /orders/{order_id} endpoint.

        Args:
            order_id (str): Printful order ID

        Returns:
            dict: {'status': str, 'tracking_number': str, 'tracking_url': str}
        """
        _logger.info("Getting order status from Printful: %s", order_id)

        success, response_data, status_code, error_message = self._make_request(
            endpoint=f'orders/{order_id}',
            method='GET'
        )

        if success:
            result = response_data.get('result', {})
            status = result.get('status', 'pending')
            tracking_number = ''
            tracking_url = ''

            # Extract tracking info from shipments
            shipments = result.get('shipments', [])
            if shipments:
                tracking_number = shipments[0].get('tracking_number', '')
                tracking_url = shipments[0].get('tracking_url', '')

            return {
                'status': status,
                'tracking_number': tracking_number,
                'tracking_url': tracking_url
            }
        else:
            _logger.error("Failed to get order status from Printful: %s", error_message)
            return {'status': 'error', 'tracking_number': '', 'tracking_url': ''}
