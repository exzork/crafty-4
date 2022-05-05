from app.classes.web.base_handler import BaseHandler


class BaseApiHandler(BaseHandler):
    def check_xsrf_cookie(self) -> None:
        # Disable XSRF protection on API routes
        pass
