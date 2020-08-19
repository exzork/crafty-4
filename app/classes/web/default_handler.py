import logging

from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class DefaultHandler(BaseHandler):

    def get(self, page=None):

        # sensible defaults
        template = "public/404.html"

        self.render(template)

    def post(self, page=None):

        # sensible defaults
        template = "public/404.html"

        self.render(template)

