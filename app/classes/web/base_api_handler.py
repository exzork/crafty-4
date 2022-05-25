from typing import Awaitable, Callable, Optional
from app.classes.web.base_handler import BaseHandler


class BaseApiHandler(BaseHandler):
    # {{{ Disable XSRF protection on API routes
    def check_xsrf_cookie(self) -> None:
        pass

    # }}}

    # {{{ 405 Method Not Allowed as JSON
    def _unimplemented_method(self, *_args: str, **_kwargs: str) -> None:
        self.finish_json(405, {"status": "error", "error": "METHOD_NOT_ALLOWED"})

    head = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    get = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    post = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    delete = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    patch = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    put = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    # }}}

    def options(self, *_, **__):
        """
        Fix CORS
        """
        # no body
        self.set_status(204)
        self.finish()
