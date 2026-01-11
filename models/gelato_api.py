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
            _logger.error(f"Gelato connection test failed: {error_message}")
            return {'success': False, 'message': error_message}
