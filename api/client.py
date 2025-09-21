from typing import Any
import aiohttp
from .exceptions import ApiClientError, ResourceNotFoundError, ApiBadRequestError

class ApiClient:
    def __init__(self, base_url: str, api_key: str, use_ssl: bool = True):
        self.base_url = base_url
        self.headers = {'X-Api-Key': api_key, 'Content-Type': 'application/json'}
        self.use_ssl = use_ssl

    async def _request(self, method: str, endpoint: str, data: dict | None = None, params: dict | None = None) -> Any:
        url = self.base_url + endpoint
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.request(
                    method, url, json=data, ssl=self.use_ssl, params=params
                ) as response:
                    if 400 <= response.status < 600:
                        message = await response.text()
                        if response.status == 404:
                            raise ResourceNotFoundError(response.status, message)
                        if response.status in [400, 409]:
                            raise ApiBadRequestError(response.status, message)
                        raise ApiClientError(response.status, message)

                    return await response.json() if response.status != 204 else None

        except aiohttp.ClientError as err:
            raise ApiClientError(status_code=500, message=str(err)) from err

    async def get(self, endpoint: str, params: dict | None = None) -> Any:
        return await self._request('GET', endpoint, params=params)

    async def post(self, endpoint: str, data: dict) -> Any:
        return await self._request('POST', endpoint, data=data)

    async def put(self, endpoint: str, data: dict) -> Any:
        return await self._request('PUT', endpoint, data=data)