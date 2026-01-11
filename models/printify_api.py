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
            _logger.error(f"Printify connection test failed: {error_message}")
            return {'success': False, 'message': error_message}
