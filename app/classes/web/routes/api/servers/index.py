import logging
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)


class ApiServersIndexHandler(BaseApiHandler):
    def get(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        # TODO: limit some columns for specific permissions

        self.finish_json(200, {"status": "ok", "data": auth_data[0]})

    def post(self):
        # TODO: create server
        self.set_status(404)
        self.finish()
