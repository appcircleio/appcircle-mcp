"""HTTP client for Appcircle API."""
import httpx
from typing import Any, Optional

from ..config.settings import settings
from .auth import get_access_token
from .logger import logger


class ApiClient:

    def __init__(self):
        self.base_url = settings.APPCIRCLE_API_URL
        self.timeout = settings.REQUEST_TIMEOUT
        self.headers = {
            "Authorization": f"Bearer {get_access_token()}",
            "Content-Type": "application/json",
        }

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

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"GET {endpoint} successful")
            return response.json()
        
    async def post(
        self,
        endpoint: str,
        json_data: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Make a POST request.
        
        Args:
            endpoint: API endpoint (e.g., "/build/v2/profiles")
            json_data: Optional JSON payload
            data: Optional form data (for multipart/form-data)
            files: Optional files for upload
            
        Returns:
            Response JSON data
        """
        logger.debug(f"POST {endpoint}")
        if json_data:
            logger.debug(f"POST payload: {json_data}")
        
        # Prepare headers (remove Content-Type for file uploads)
        headers = self.headers.copy()
        if files:
            headers.pop("Content-Type", None)  # Let httpx set it for multipart
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                headers=headers,
                json=json_data,
                data=data,
                files=files,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"POST {endpoint} successful")
            return response.json()
    
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
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=json_data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"PATCH {endpoint} successful")
            return response.json()
        
    async def delete(self, endpoint: str) -> Any:
        """
        Make a DELETE request.
        
        Args:
            endpoint: API endpoint (e.g., "/build/v2/profiles/{id}")
            
        Returns:
            Response JSON data
        """
        logger.debug(f"DELETE {endpoint}")
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"DELETE {endpoint} successful")
            return response.json()
    
    async def put(
        self,
        endpoint: str,
        json_data: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Make a PUT request.
        
        Args:
            endpoint: API endpoint (e.g., "/build/v2/profiles/{id}")
            json_data: Optional JSON payload for full update
            
        Returns:
            Response JSON data
        """
        logger.debug(f"PUT {endpoint}")
        if json_data:
            logger.debug(f"PUT payload: {json_data}")
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=json_data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"PUT {endpoint} successful")
            return response.json()