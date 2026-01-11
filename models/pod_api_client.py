# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
import requests
from abc import ABC, abstractmethod
from odoo import _

_logger = logging.getLogger(__name__)


class PodAPIClient(ABC):
    """Abstract base class for POD provider API clients."""

    def __init__(self, api_key, api_secret=None, base_url=None):
        """
        Initialize the API client.

        Args:
            api_key (str): API key for authentication
            api_secret (str, optional): API secret for authentication
            base_url (str, optional): Base URL for the API
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.timeout = 30

    def _make_request(self, endpoint, method='GET', data=None):
        """
        Make an HTTP request to the API.

        Args:
            endpoint (str): API endpoint path
            method (str): HTTP method (GET, POST, PUT, DELETE)
            data (dict, optional): Request payload for POST/PUT

        Returns:
            tuple: (success: bool, response_data: dict, status_code: int, error_message: str)
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        _logger.info("Making %s request to %s", method, url)

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )

            _logger.info("Response status: %s", response.status_code)

            # Check if request was successful
            if response.status_code >= 200 and response.status_code < 300:
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = {}
                return (True, response_data, response.status_code, None)
            else:
                # Handle error responses
                error_message = self._parse_error_response(response)
                _logger.error(f"API request failed: {error_message}")
                return (False, None, response.status_code, error_message)

        except requests.exceptions.Timeout:
            error_message = _("Connection timeout: Request took longer than %s seconds") % self.timeout
            _logger.error(error_message)
            return (False, None, None, error_message)

        except requests.exceptions.ConnectionError as e:
            error_message = _("Connection failed: Unable to reach the server")
            _logger.error("%s: %s", error_message, str(e))
            return (False, None, None, error_message)

        except requests.exceptions.RequestException as e:
            error_message = _("Request failed: %s") % str(e)
            _logger.error(error_message)
            return (False, None, None, error_message)

    def _parse_error_response(self, response):
        """
        Parse error message from API response.

        Args:
            response: requests.Response object

        Returns:
            str: User-friendly error message
        """
        status_code = response.status_code

        # Try to get error message from response body
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                # Try common error message keys
                error_msg = (error_data.get('error') or 
                           error_data.get('message') or 
                           error_data.get('error_message') or
                           response.text)
            else:
                error_msg = response.text
        except ValueError:
            error_msg = response.text

        # Create user-friendly message based on status code
        if status_code == 401:
            return _("Connection failed (%s): Invalid API key") % status_code
        elif status_code == 403:
            return _("Connection failed (%s): Access forbidden") % status_code
        elif status_code == 404:
            return _("Connection failed (%s): Endpoint not found") % status_code
        elif status_code >= 500:
            return _("Connection failed (%s): Server error - %s") % (status_code, error_msg)
        else:
            return _("Connection failed (%s): %s") % (status_code, error_msg)

    @abstractmethod
    def _get_headers(self):
        """
        Get authentication headers for the API.
        Must be implemented by each provider.

        Returns:
            dict: Headers dictionary
        """
        pass

    @abstractmethod
    def test_connection(self):
        """
        Test the API connection.
        Must be implemented by each provider.

        Returns:
            dict: {'success': bool, 'message': str}
        """
        pass
