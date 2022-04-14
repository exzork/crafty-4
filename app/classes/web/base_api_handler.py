from app.classes.web.base_handler import BaseHandler


class BaseApiHandler(BaseHandler):
    def check_xsrf_cookie(self):
        # Disable XSRF protection on API routes
        pass
