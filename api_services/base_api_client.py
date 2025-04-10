"""
Base API client for Staples services.
"""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import requests
from utils.observability import log_api_call

logger = logging.getLogger(__name__)


class StaplesApiClient:
    """Base client for Staples API services."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        mock_mode: bool = True,
    ):
        """
        Initialize the Staples API client.

        Args:
            base_url: Base URL for the API endpoint. If None, will use environment variable.
            api_key: API key for authentication. If None, will use environment variable.
            timeout: Request timeout in seconds.
            mock_mode: If True, will use mock data instead of making actual API calls.
        """
        self.base_url = base_url or os.environ.get("STAPLES_API_URL", "https://api.staples.com/v1/")
        self.api_key = api_key or os.environ.get("STAPLES_API_KEY", "mock-api-key")
        self.timeout = timeout
        self.mock_mode = mock_mode
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Staples Brain/1.0",
            }
        )

    def _get_url(self, endpoint: str) -> str:
        """
        Construct the full URL for the given endpoint.

        Args:
            endpoint: API endpoint.

        Returns:
            Full URL.
        """
        return urljoin(self.base_url, endpoint.lstrip("/"))

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        mock_response: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint.
            params: Query parameters.
            data: Request body.
            mock_response: Mock response to return when in mock mode.

        Returns:
            API response.
        """
        url = self._get_url(endpoint)
        start_time = time.time()
        
        try:
            if self.mock_mode and mock_response is not None:
                logger.info(f"Mock API call to {url} with mock response")
                response_data = mock_response
                status_code = 200
            else:
                logger.info(f"Making {method} request to {url}")
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    timeout=self.timeout,
                )
                status_code = response.status_code
                response.raise_for_status()
                response_data = response.json()
            
            duration = time.time() - start_time
            log_api_call(
                api_name="staples_api",
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                duration=duration,
                error=None,
            )
            
            return response_data
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            error_message = str(e)
            logger.error(f"API request failed: {error_message}")
            
            log_api_call(
                api_name="staples_api",
                endpoint=endpoint,
                method=method,
                status_code=getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500,
                duration=duration,
                error=error_message,
            )
            
            if self.mock_mode and mock_response is not None:
                logger.warning(f"Returning mock response after API failure")
                return mock_response
            
            raise

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        mock_response: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a GET request.

        Args:
            endpoint: API endpoint.
            params: Query parameters.
            mock_response: Mock response to return when in mock mode.

        Returns:
            API response.
        """
        return self._make_request("GET", endpoint, params=params, mock_response=mock_response)

    def post(
        self,
        endpoint: str,
        data: Dict[str, Any],
        mock_response: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint.
            data: Request body.
            mock_response: Mock response to return when in mock mode.

        Returns:
            API response.
        """
        return self._make_request("POST", endpoint, data=data, mock_response=mock_response)

    def put(
        self,
        endpoint: str,
        data: Dict[str, Any],
        mock_response: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a PUT request.

        Args:
            endpoint: API endpoint.
            data: Request body.
            mock_response: Mock response to return when in mock mode.

        Returns:
            API response.
        """
        return self._make_request("PUT", endpoint, data=data, mock_response=mock_response)

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        mock_response: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a DELETE request.

        Args:
            endpoint: API endpoint.
            params: Query parameters.
            mock_response: Mock response to return when in mock mode.

        Returns:
            API response.
        """
        return self._make_request("DELETE", endpoint, params=params, mock_response=mock_response)