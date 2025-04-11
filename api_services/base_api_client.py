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
from utils.observability import log_api_call, record_error
from utils.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenException

logger = logging.getLogger(__name__)


class StaplesApiClient:
    """Base client for Staples API services."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        mock_mode: bool = True,
        service_name: str = "staples_api",
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
    ):
        """
        Initialize the Staples API client.

        Args:
            base_url: Base URL for the API endpoint. If None, will use environment variable.
            api_key: API key for authentication. If None, will use environment variable.
            timeout: Request timeout in seconds.
            mock_mode: If True, will use mock data instead of making actual API calls.
            service_name: Name of the service, used for circuit breaker and telemetry.
            failure_threshold: Number of failures before opening the circuit breaker.
            recovery_timeout: Seconds to wait before trying to recover a failed circuit.
        """
        self.base_url = base_url or os.environ.get("STAPLES_API_URL", "https://api.staples.com/v1/")
        self.api_key = api_key or os.environ.get("STAPLES_API_KEY", "mock-api-key")
        self.timeout = timeout
        self.mock_mode = mock_mode
        self.service_name = service_name
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Staples Brain/1.0",
            }
        )
        
        # Create a circuit breaker for this API client
        self.circuit_breaker = get_circuit_breaker(
            name=f"{service_name}_circuit",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
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
        Make an API request with circuit breaker protection.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint.
            params: Query parameters.
            data: Request body.
            mock_response: Mock response to return when in mock mode.

        Returns:
            API response.
            
        Raises:
            CircuitBreakerOpenException: If the circuit breaker is open.
            requests.exceptions.RequestException: If the request fails.
        """
        url = self._get_url(endpoint)
        
        # Skip circuit breaker if we're in mock mode and have a mock response
        if self.mock_mode and mock_response is not None:
            logger.info(f"Mock API call to {url} with mock response")
            return mock_response
        
        # Define the actual request function to be protected by the circuit breaker
        def make_live_request() -> Dict[str, Any]:
            start_time = time.time()
            try:
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
                    api_name=self.service_name,
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
                    api_name=self.service_name,
                    endpoint=endpoint,
                    method=method,
                    status_code=getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500,
                    duration=duration,
                    error=error_message,
                )
                
                raise
        
        # Define a fallback function to use if the circuit is open
        def fallback_function() -> Dict[str, Any]:
            logger.warning(f"Circuit '{self.circuit_breaker.name}' is open, using fallback")
            if self.mock_mode and mock_response is not None:
                logger.info(f"Returning mock response as fallback for {url}")
                return mock_response
                
            # If no mock response is available, we have to let the caller know the service is unavailable
            raise CircuitBreakerOpenException(
                f"Service {self.service_name} is currently unavailable"
            )
        
        try:
            # Execute the request with circuit breaker protection
            return self.circuit_breaker.execute(make_live_request)
        except CircuitBreakerOpenException:
            # If the circuit is open and we have a fallback, use it
            return fallback_function()
        except requests.exceptions.RequestException as e:
            # If the request failed but we have a mock response, use it as fallback in mock mode
            if self.mock_mode and mock_response is not None:
                logger.warning(f"Request failed, returning mock response for {url}: {str(e)}")
                return mock_response
            
            # Otherwise, re-raise the exception
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