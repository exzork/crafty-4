from datetime import datetime
import logging
import re

from platformdirs import user_cache_path

from app.classes.controllers.crafty_perms_controller import Enum_Permissions_Crafty
from app.classes.controllers.server_perms_controller import Enum_Permissions_Server
from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)
bearer_pattern = re.compile(r"^Bearer", flags=re.IGNORECASE)


class ApiHandler(BaseHandler):
    def return_response(self, status: int, data: dict):
        # Define a standardized response
        self.set_status(status)
        self.write(data)

    def check_xsrf_cookie(self):
        # Disable CSRF protection on API routes
        pass

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
        self.permissions = {
            "Commands": Enum_Permissions_Server.Commands,
            "Terminal": Enum_Permissions_Server.Terminal,
            "Logs": Enum_Permissions_Server.Logs,
            "Schedule": Enum_Permissions_Server.Schedule,
            "Backup": Enum_Permissions_Server.Backup,
            "Files": Enum_Permissions_Server.Files,
            "Config": Enum_Permissions_Server.Config,
            "Players": Enum_Permissions_Server.Players,
            "Server_Creation": Enum_Permissions_Crafty.Server_Creation,
            "User_Config": Enum_Permissions_Crafty.User_Config,
            "Roles_Config": Enum_Permissions_Crafty.Roles_Config,
        }
        try:
            logger.debug("Searching for specified token")

            api_token = self.get_argument("token", "")
            self.api_token = api_token
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
        user_obj = self.controller.users.get_user_by_api_token(self.api_token)
        if not authenticated:
            return
        if user_obj["superuser"]:
            raw_stats = self.controller.servers.get_all_servers_stats()
        else:
            raw_stats = self.controller.servers.get_authorized_servers_stats(
                user_obj["user_id"]
            )
        stats = []
        for rs in raw_stats:
            s = {}
            for k, v in rs["server_data"].items():
                if isinstance(v, datetime):
                    s[k] = v.timestamp()
                else:
                    s[k] = v
            stats.append(s)

        # Get server stats
        # TODO Check perms
        self.finish(self.write({"servers": stats}))


class NodeStats(ApiHandler):
    def get(self):
        """Get stats for particular node"""
        authenticated = self.authenticate_user()
        if not authenticated:
            return

        # Get node stats
        node_stats = self.controller.stats.get_node_stats()
        self.return_response(200, {"code": node_stats["node_stats"]})


class SendCommand(ApiHandler):
    def post(self):
        user = self.authenticate_user()

        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return
        server_id = self.get_argument("id")

        if (
            not user_obj["user_id"]
            in self.controller.server_perms.get_server_user_list(server_id)
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")
            return

        if not self.permissions[
            "Commands"
        ] in self.controller.server_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token), server_id
        ):
            self.access_denied(user)
            return

        command = self.get_argument("command", default=None, strip=True)
        server_id = self.get_argument("id")
        if command:
            server = self.controller.get_server_obj(server_id)
            if server.check_running:
                server.send_command(command)
                self.return_response(200, {"run": True})
            else:
                self.return_response(200, {"error": "SER_NOT_RUNNING"})
        else:
            self.return_response(200, {"error": "NO_COMMAND"})


class ServerBackup(ApiHandler):
    def post(self):
        user = self.authenticate_user()

        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return
        server_id = self.get_argument("id")

        if (
            not user_obj["user_id"]
            in self.controller.server_perms.get_server_user_list(server_id)
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")
            return

        if not self.permissions[
            "Backup"
        ] in self.controller.server_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token), server_id
        ):
            self.access_denied(user)
            return

        server = self.controller.get_server_obj(server_id)

        server.backup_server()

        self.return_response(200, {"code": "SER_BAK_CALLED"})


class StartServer(ApiHandler):
    def post(self):
        user = self.authenticate_user()
        remote_ip = self.get_remote_ip()

        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return
        server_id = self.get_argument("id")

        if (
            not user_obj["user_id"]
            in self.controller.server_perms.get_server_user_list(server_id)
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")
            return
        elif not self.permissions[
            "Commands"
        ] in self.controller.server_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token), server_id
        ):
            self.access_denied("unknown")
            return

        server = self.controller.get_server_obj(server_id)

        if not server.check_running():
            self.controller.management.send_command(
                user_obj["user_id"], server_id, remote_ip, "start_server"
            )
            self.return_response(200, {"code": "SER_START_CALLED"})
        else:
            self.return_response(500, {"error": "SER_RUNNING"})


class StopServer(ApiHandler):
    def post(self):
        user = self.authenticate_user()
        remote_ip = self.get_remote_ip()

        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return
        server_id = self.get_argument("id")

        if (
            not user_obj["user_id"]
            in self.controller.server_perms.get_server_user_list(server_id)
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")

        if not self.permissions[
            "Commands"
        ] in self.controller.server_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token), server_id
        ):
            self.access_denied(user)
            return

        server = self.controller.get_server_obj(server_id)

        if server.check_running():
            self.controller.management.send_command(
                user, server_id, remote_ip, "stop_server"
            )

            self.return_response(200, {"code": "SER_STOP_CALLED"})
        else:
            self.return_response(500, {"error": "SER_NOT_RUNNING"})


class RestartServer(ApiHandler):
    def post(self):
        user = self.authenticate_user()
        remote_ip = self.get_remote_ip()
        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return
        server_id = self.get_argument("id")

        if not user_obj["user_id"] in self.controller.server_perms.get_server_user_list(
            server_id
        ):
            self.access_denied("unknown")

        if not self.permissions[
            "Commands"
        ] in self.controller.server_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token), server_id
        ):
            self.access_denied(user)

        self.controller.management.send_command(
            user, server_id, remote_ip, "restart_server"
        )
        self.return_response(200, {"code": "SER_RESTART_CALLED"})


class CreateUser(ApiHandler):
    def post(self):
        user = self.authenticate_user()
        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        user_perms = self.controller.crafty_perms.get_crafty_permissions_list(
            user_obj["user_id"]
        )
        if (
            not self.permissions["User_Config"] in user_perms
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")
            return

        if user is None:
            self.access_denied("unknown")
            return

        if not self.permissions[
            "User_Config"
        ] in self.controller.crafty_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token)
        ):
            self.access_denied(user)
            return

        new_username = self.get_argument("username")
        new_pass = self.get_argument("password")

        if new_username:
            self.controller.users.add_user(
                new_username, new_pass, "default@example.com", True, False
            )

            self.return_response(
                200,
                {
                    "code": "COMPLETE",
                    "username": new_username,
                    "password": new_pass,
                },
            )
        else:
            self.return_response(
                500,
                {
                    "error": "MISSING_PARAMS",
                    "info": "Some paramaters failed validation",
                },
            )


class DeleteUser(ApiHandler):
    def post(self):
        user = self.authenticate_user()

        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        user_perms = self.controller.crafty_perms.get_crafty_permissions_list(
            user_obj["user_id"]
        )

        if (
            not self.permissions["User_Config"] in user_perms
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")
            return

        if user is None:
            self.access_denied("unknown")
            return

        if not self.permissions[
            "User_Config"
        ] in self.controller.crafty_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token)
        ):
            self.access_denied(user)
            return

        user_id = self.get_argument("user_id", None, True)
        user_to_del = self.controller.users.get_user_by_id(user_id)

        if user_to_del["superuser"]:
            self.return_response(
                500,
                {"error": "NOT_ALLOWED", "info": "You cannot delete a super user"},
            )
        else:
            if user_id:
                self.controller.users.remove_user(user_id)
                self.return_response(200, {"code": "COMPLETED"})


class ListServers(ApiHandler):
    def get(self):
        user = self.authenticate_user()
        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return

        if self.api_token is None:
            self.access_denied("unknown")
            return

        if user_obj["superuser"]:
            servers = self.controller.servers.get_all_defined_servers()
            servers = [str(i) for i in servers]
        else:
            servers = self.controller.servers.get_authorized_servers(
                user_obj["user_id"]
            )
            servers = [str(i) for i in servers]

        self.return_response(
            200,
            {
                "code": "COMPLETED",
                "servers": servers,
            },
        )
