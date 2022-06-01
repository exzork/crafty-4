import logging
from app.classes.models.server_stats import HelperServerStats
from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)


class ApiServersServerStatsHandler(BaseApiHandler):
    def get(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": HelperServerStats.get_server_stats_by_id(server_id),
            },
        )
