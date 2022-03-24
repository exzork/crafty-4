import logging
import re

from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)
bearer_pattern = re.compile(r"^Bearer", flags=re.IGNORECASE)


class ApiHandler(BaseHandler):
    def return_response(self, status: int, data: dict):
        # Define a standardized response
        self.set_status(status)
        self.write(data)

    def access_denied(self, user, reason=""):
        if reason:
            reason = " because " + reason
        logger.info(
            "User %s from IP %s was denied access to the API route "
            + self.request.path
            + reason,
            user,
            self.get_remote_ip(),
        )
        self.finish(
            self.return_response(
                403,
                {
                    "error": "ACCESS_DENIED",
                    "info": "You were denied access to the requested resource",
                },
            )
        )

    def authenticate_user(self) -> bool:
        try:
            logger.debug("Searching for specified token")

            api_token = self.get_argument("token", "")
            if api_token is None and self.request.headers.get("Authorization"):
                api_token = bearer_pattern.sub(
                    "", self.request.headers.get("Authorization")
                )
            elif api_token is None:
                api_token = self.get_cookie("token")
            user_data = self.controller.users.get_user_by_api_token(api_token)

            logger.debug("Checking results")
            if user_data:
                # Login successful! Check perms
                logger.info(f"User {user_data['username']} has authenticated to API")
                # TODO: Role check

                return True  # This is to set the "authenticated"
            else:
                logging.debug("Auth unsuccessful")
                self.access_denied("unknown", "the user provided an invalid token")
                return False
        except Exception as e:
            logger.warning("An error occured while authenticating an API user: %s", e)
            self.finish(
                self.return_response(
                    403,
                    {
                        "error": "ACCESS_DENIED",
                        "info": "An error occured while authenticating the user",
                    },
                )
            )
            return False


class ServersStats(ApiHandler):
    def get(self):
        """Get details about all servers"""
        authenticated = self.authenticate_user()
        if not authenticated:
            return

        # Get server stats
        # TODO Check perms
        self.finish(self.write({"servers": self.controller.stats.get_servers_stats()}))


class NodeStats(ApiHandler):
    def get(self):
        """Get stats for particular node"""
        authenticated = self.authenticate_user()
        if not authenticated:
            return

        # Get node stats
        node_stats = self.controller.stats.get_node_stats()
        node_stats.pop("servers")
        self.finish(self.write(node_stats))
