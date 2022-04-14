import logging
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)


class ApiServersServerPublicHandler(BaseApiHandler):
    def get(self, server_id):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        server_obj = self.controller.servers.get_server_obj(server_id)

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": {
                    key: getattr(server_obj, key)
                    for key in ["server_id", "created", "server_name", "type"]
                },
            },
        )
