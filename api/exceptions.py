class ApiClientError(Exception):
    """Базовий виняток для помилок API-клієнта."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")

class ResourceNotFoundError(ApiClientError):
    """Виняток для помилок 404 Not Found."""
    pass

class ApiBadRequestError(ApiClientError):
    """Виняток для помилок 400 Bad Request / 409 Conflict."""
    pass