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
        Create a new order in Gelato.
        Calls appropriate Gelato endpoint for order creation.

        Args:
            order_data (dict): Order data with recipient and items

        Returns:
            dict: {'success': bool, 'order_id': str, 'message': str}
        """
        _logger.info("Creating order in Gelato")

        # Transform order data to Gelato format
        gelato_data = {
            'orderReferenceId': order_data.get('external_id', ''),
            'customerReferenceId': order_data.get('customer_id', ''),
            'shippingAddress': {
                'firstName': order_data['recipient'].get('name', '').split()[0] if order_data['recipient'].get('name') else '',
                'lastName': ' '.join(order_data['recipient'].get('name', '').split()[1:]) if len(order_data['recipient'].get('name', '').split()) > 1 else '',
                'addressLine1': order_data['recipient'].get('address1', ''),
                'addressLine2': order_data['recipient'].get('address2', ''),
                'city': order_data['recipient'].get('city', ''),
                'postCode': order_data['recipient'].get('zip', ''),
                'country': order_data['recipient'].get('country', ''),
                'email': order_data['recipient'].get('email', ''),
                'phone': order_data['recipient'].get('phone', ''),
            },
            'orderItems': []
        }

        # Add state if available
        if order_data['recipient'].get('state'):
            gelato_data['shippingAddress']['state'] = order_data['recipient']['state']

        # Add order items
        for item in order_data.get('items', []):
            gelato_data['orderItems'].append({
                'productUid': item.get('product_id'),
                'variantUid': item.get('variant_id', ''),
                'quantity': item.get('quantity', 1),
            })

        success, response_data, status_code, error_message = self._make_request(
            endpoint='orders',
            method='POST',
            data=gelato_data
        )

        if success:
            order_id = response_data.get('orderUid', response_data.get('id', ''))
            _logger.info("Order created successfully in Gelato: %s", order_id)
            return {
                'success': True,
                'order_id': str(order_id),
                'message': _("Order created successfully")
            }
        else:
            _logger.error("Failed to create order in Gelato: %s", error_message)
            return {
                'success': False,
                'message': error_message
            }

    def get_order_status(self, order_id):
        """
        Get order status from Gelato.
        Calls GET /orders/{order_id} endpoint.

        Args:
            order_id (str): Gelato order ID

        Returns:
            dict: {'status': str, 'tracking_number': str, 'tracking_url': str}
        """
        _logger.info("Getting order status from Gelato: %s", order_id)

        success, response_data, status_code, error_message = self._make_request(
            endpoint=f'orders/{order_id}',
            method='GET'
        )

        if success:
            status = response_data.get('status', 'pending')
            tracking_number = ''
            tracking_url = ''

            # Extract tracking info
            shipments = response_data.get('shipments', [])
            if shipments:
                tracking_number = shipments[0].get('trackingNumber', '')
                tracking_url = shipments[0].get('trackingUrl', '')

            return {
                'status': status,
                'tracking_number': tracking_number,
                'tracking_url': tracking_url
            }
        else:
            _logger.error("Failed to get order status from Gelato: %s", error_message)
            return {'status': 'error', 'tracking_number': '', 'tracking_url': ''}
