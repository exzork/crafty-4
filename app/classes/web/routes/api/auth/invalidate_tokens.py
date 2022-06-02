import datetime
import logging
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)


class ApiAuthInvalidateTokensHandler(BaseApiHandler):
    def post(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        logger.debug(f"Invalidate tokens for user {auth_data[4]['user_id']}")
        self.controller.users.raw_update_user(
            auth_data[4]["user_id"], {"valid_tokens_from": datetime.datetime.now()}
        )

        self.finish_json(200, {"status": "ok"})
