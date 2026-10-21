"""HTTP client for Appcircle API."""
import httpx
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from ..config.settings import settings
from .auth import get_access_token
from .logger import logger

# Characters that are never part of a legitimate endpoint path (query/fragment
# delimiters, backslash, percent-encoding)
_FORBIDDEN_ENDPOINT_CHARS = frozenset("?#\\%")


class ApiClient:

    def __init__(self):
        self.base_url = settings.APPCIRCLE_API_URL
        self.timeout = settings.REQUEST_TIMEOUT
        self.headers = {
            "Authorization": f"Bearer {get_access_token()}",
            "Content-Type": "application/json",
        }
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ApiClient":
        """Enter a connection-reuse session: subsequent calls share one httpx client."""
        self._client = httpx.AsyncClient()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[httpx.AsyncClient]:
        """Yield the shared client if inside an `async with ApiClient()` session,
        otherwise fall back to a fresh one-off client (today's behavior)."""
        if self._client is not None:
            yield self._client
        else:
            async with httpx.AsyncClient() as client:
                yield client

    def _url(self, endpoint: str) -> str:
        """Build the full request URL, rejecting endpoints that could escape their intended path."""
        if (
            not endpoint.startswith("/")
            or _FORBIDDEN_ENDPOINT_CHARS.intersection(endpoint)
            or any(segment in (".", "..") for segment in endpoint.split("/"))
        ):
            raise ValueError(f"Invalid endpoint path: {endpoint!r}")
        return f"{self.base_url}{endpoint}"

    async def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None
    ) -> Any:
        """
        Make a GET request.
        
        Args:
            endpoint: API endpoint (e.g., "/build/v2/profiles")
            params: Optional query parameters
            
        Returns:
            Response JSON data
        """
        logger.debug(f"GET {endpoint} with params: {params}")

        async with self._get_client() as client:
            response = await client.get(
                self._url(endpoint),
                headers=self.headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"GET {endpoint} successful")
            if not response.content:
                return {}
            try:
                return response.json()
            except ValueError:
                return {}

    async def get_text(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Make a GET request and return the raw text body (not JSON).

        Used for endpoints that return plain text, such as build/publish logs.

        Args:
            endpoint: API endpoint (e.g., "/build/v2/commits/{id}/builds/{id}/logs")
            params: Optional query parameters

        Returns:
            Response body as text
        """
        logger.debug(f"GET {endpoint} (text) with params: {params}")

        async with self._get_client() as client:
            response = await client.get(
                self._url(endpoint),
                headers=self.headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"GET {endpoint} (text) successful")
            return response.text

    async def post(
        self,
        endpoint: str,
        json_data: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint (e.g., "/build/v2/profiles")
            json_data: Optional JSON payload
            data: Optional form data (for multipart/form-data)
            files: Optional files for upload
            params: Optional query parameters

        Returns:
            Response JSON data
        """
        logger.debug(f"POST {endpoint} with params: {params}")

        # Prepare headers (remove Content-Type for file uploads)
        headers = self.headers.copy()
        if files:
            headers.pop("Content-Type", None)  # Let httpx set it for multipart

        async with self._get_client() as client:
            response = await client.post(
                self._url(endpoint),
                headers=headers,
                json=json_data,
                data=data,
                files=files,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"POST {endpoint} successful")
            if not response.content:
                return {}
            try:
                return response.json()
            except ValueError:
                return {}

    async def patch(
        self,
        endpoint: str,
        json_data: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Make a PATCH request.
        
        Args:
            endpoint: API endpoint (e.g., "/build/v2/profiles/{id}")
            json_data: Optional JSON payload for partial update
            
        Returns:
            Response JSON data
        """
        logger.debug(f"PATCH {endpoint}")
        if json_data:
            logger.debug(f"PATCH payload: {json_data}")

        async with self._get_client() as client:
            response = await client.patch(
                self._url(endpoint),
                headers=self.headers,
                json=json_data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"PATCH {endpoint} successful")
            if not response.content:
                return {}
            try:
                return response.json()
            except ValueError:
                return {}
        
    async def delete(self, endpoint: str) -> Any:
        """
        Make a DELETE request.
        
        Args:
            endpoint: API endpoint (e.g., "/build/v2/profiles/{id}")
            
        Returns:
            Response JSON data
        """
        logger.debug(f"DELETE {endpoint}")

        async with self._get_client() as client:
            response = await client.delete(
                self._url(endpoint),
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"DELETE {endpoint} successful")
            if not response.content:
                return {}
            try:
                return response.json()
            except ValueError:
                return {}
    
    async def put(
        self,
        endpoint: str,
        json_data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Make a PUT request.

        Args:
            endpoint: API endpoint (e.g., "/build/v2/profiles/{id}")
            json_data: Optional JSON payload for full update
            params: Optional query parameters

        Returns:
            Response JSON data
        """
        logger.debug(f"PUT {endpoint} with params: {params}")
        if json_data:
            logger.debug(f"PUT payload: {json_data}")

        async with self._get_client() as client:
            response = await client.put(
                self._url(endpoint),
                headers=self.headers,
                json=json_data,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"PUT {endpoint} successful")
            if not response.content:
                return {}
            try:
                return response.json()
            except ValueError:
                return {}