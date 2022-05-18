from typing import Awaitable, Callable, Optional
from app.classes.web.base_api_handler import BaseApiHandler


class ApiNotFoundHandler(BaseApiHandler):
    def _not_found(self, page: str) -> None:
        self.finish_json(
            404,
            {"status": "error", "error": "API_HANDLER_NOT_FOUND", "page": page},
        )

    head = _not_found  # type: Callable[..., Optional[Awaitable[None]]]
    get = _not_found  # type: Callable[..., Optional[Awaitable[None]]]
    post = _not_found  # type: Callable[..., Optional[Awaitable[None]]]
    delete = _not_found  # type: Callable[..., Optional[Awaitable[None]]]
    patch = _not_found  # type: Callable[..., Optional[Awaitable[None]]]
    put = _not_found  # type: Callable[..., Optional[Awaitable[None]]]
    options = _not_found  # type: Callable[..., Optional[Awaitable[None]]]
