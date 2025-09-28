from typing import Any
import aiohttp
from .exceptions import ApiClientError, ResourceNotFoundError, ApiBadRequestError

class ApiClient:
    def __init__(self, base_url: str, api_key: str, use_ssl: bool = True):
        self.base_url = base_url
        self.default_headers = {'X-Api-Key': api_key, 'Content-Type': 'application/json'}
        self.use_ssl = use_ssl
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        """Створює сесію при вході в асинхронний контекст."""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закриває сесію при виході з асинхронного контексту."""
        if self._session:
            await self._session.close()

    async def _request(self, method: str, endpoint: str, data: dict | None = None, 
                       params: dict | None = None, extra_headers: dict | None = None) -> Any:
        if not self._session:
            raise RuntimeError("ApiClient session not started. Use 'async with ApiClient(...):'")

        url = self.base_url + endpoint

        request_headers = self.default_headers.copy()
        if extra_headers:
            request_headers.update(extra_headers)

        try:
            async with self._session.request(
                method, url, json=data, ssl=self.use_ssl, params=params, headers=request_headers
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

    async def post(self, endpoint: str, data: dict, extra_headers: dict | None = None) -> Any:
        return await self._request('POST', endpoint, data=data, extra_headers=extra_headers)

    async def put(self, endpoint: str, data: dict) -> Any:
        return await self._request('PUT', endpoint, data=data)