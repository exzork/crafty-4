import os
import logging
import json
import typing as t

from app.classes.controllers.roles_controller import RolesController
from app.classes.models.servers import HelperServers
from app.classes.models.users import HelperUsers, ApiKeys
from app.classes.models.server_permissions import (
    PermissionsServers,
    EnumPermissionsServer,
)
from app.classes.shared.helpers import Helpers
from app.classes.shared.main_models import DatabaseShortcuts

logger = logging.getLogger(__name__)


class ServersController:
    def __init__(self, servers_helper):
        self.servers_helper = servers_helper

    # **********************************************************************************
    #                                   Generic Servers Methods
    # **********************************************************************************
    def create_server(
        self,
        name: str,
        server_uuid: str,
        server_dir: str,
        backup_path: str,
        server_command: str,
        server_file: str,
        server_log_file: str,
        server_stop: str,
        server_type: str,
        server_port: int = 25565,
        server_host: str = "127.0.0.1",
    ) -> int:
        """Create a server in the database

        Args:
            name: The name of the server
            server_uuid: This is the UUID of the server
            server_dir: The directory where the server is located
            backup_path: The path to the backup folder
            server_command: The command to start the server
            server_file: The name of the server file
            server_log_file: The path to the server log file
            server_stop: This is the command to stop the server
            server_type: This is the type of server you're creating.
            server_port: The port the server will be monitored on, defaults to 25565
            server_host: The host the server will be monitored on, defaults to 127.0.0.1

        Returns:
            int: The new server's id

        Raises:
            PeeweeException: If the server already exists
        """
        return HelperServers.create_server(
            name,
            server_uuid,
            server_dir,
            backup_path,
            server_command,
            server_file,
            server_log_file,
            server_stop,
            server_type,
            server_port,
            server_host,
        )

    @staticmethod
    def get_server_obj(server_id):
        return HelperServers.get_server_obj(server_id)

    @staticmethod
    def update_server(server_obj):
        return HelperServers.update_server(server_obj)

    @staticmethod
    def set_download(server_id):
        return HelperServers.set_download(server_id)

    @staticmethod
    def finish_download(server_id):
        return HelperServers.finish_download(server_id)

    @staticmethod
    def get_download_status(server_id):
        return HelperServers.get_download_status(server_id)

    def remove_server(self, server_id):
        roles_list = PermissionsServers.get_roles_from_server(server_id)
        for role in roles_list:
            role_id = role.role_id
            role_data = RolesController.get_role_with_servers(role_id)
            role_data["servers"] = {server_id}
            PermissionsServers.delete_roles_permissions(role_id, role_data["servers"])
        PermissionsServers.remove_roles_of_server(server_id)
        self.servers_helper.remove_server(server_id)

    @staticmethod
    def get_server_data_by_id(server_id):
        return HelperServers.get_server_data_by_id(server_id)

    # **********************************************************************************
    #                                     Servers Methods
    # **********************************************************************************
    @staticmethod
    def get_all_defined_servers():
        return HelperServers.get_all_defined_servers()

    @staticmethod
    def get_authorized_servers(user_id):
        server_data: t.List[t.Dict[str, t.Any]] = []
        user_roles = HelperUsers.user_role_query(user_id)
        for user in user_roles:
            role_servers = PermissionsServers.get_role_servers_from_role_id(
                user.role_id
            )
            for role in role_servers:
                server_data.append(HelperServers.get_server_data_by_id(role.server_id))

        return server_data

    @staticmethod
    def get_authorized_users(server_id: str):
        user_ids: t.Set[int] = set()
        roles_list = PermissionsServers.get_roles_from_server(server_id)
        for role in roles_list:
            role_users = HelperUsers.get_users_from_role(role.role_id)
            for user_role in role_users:
                user_ids.add(user_role.user_id)

        for user_id in HelperUsers.get_super_user_list():
            user_ids.add(user_id)

        return user_ids

    @staticmethod
    def get_all_servers_stats():
        return HelperServers.get_all_servers_stats()

    @staticmethod
    def get_authorized_servers_stats_api_key(api_key: ApiKeys):
        server_data = []
        authorized_servers = ServersController.get_authorized_servers(
            api_key.user.user_id  # TODO: API key authorized servers?
        )

        for server in authorized_servers:
            latest = HelperServers.get_latest_server_stats(server.get("server_id"))
            key_permissions = PermissionsServers.get_api_key_permissions_list(
                api_key, server.get("server_id")
            )
            if EnumPermissionsServer.COMMANDS in key_permissions:
                user_command_permission = True
            else:
                user_command_permission = False
            server_data.append(
                {
                    "server_data": server,
                    "stats": DatabaseShortcuts.return_rows(latest)[0],
                    "user_command_permission": user_command_permission,
                }
            )
        return server_data

    @staticmethod
    def get_authorized_servers_stats(user_id):
        server_data = []
        authorized_servers = ServersController.get_authorized_servers(user_id)

        for server in authorized_servers:
            latest = HelperServers.get_latest_server_stats(server.get("server_id"))
            # TODO
            user_permissions = PermissionsServers.get_user_id_permissions_list(
                user_id, server.get("server_id")
            )
            if EnumPermissionsServer.COMMANDS in user_permissions:
                user_command_permission = True
            else:
                user_command_permission = False
            server_data.append(
                {
                    "server_data": server,
                    "stats": DatabaseShortcuts.return_rows(latest)[0],
                    "user_command_permission": user_command_permission,
                }
            )

        return server_data

    @staticmethod
    def get_server_friendly_name(server_id):
        return HelperServers.get_server_friendly_name(server_id)

    # **********************************************************************************
    #                                    Servers_Stats Methods
    # **********************************************************************************
    @staticmethod
    def get_server_stats_by_id(server_id):
        return HelperServers.get_server_stats_by_id(server_id)

    @staticmethod
    def server_id_exists(server_id):
        return HelperServers.server_id_exists(server_id)

    @staticmethod
    def get_server_type_by_id(server_id):
        return HelperServers.get_server_type_by_id(server_id)

    @staticmethod
    def server_id_authorized(server_id_a, user_id):
        user_roles = HelperUsers.user_role_query(user_id)
        for role in user_roles:
            for server_id_b in PermissionsServers.get_role_servers_from_role_id(
                role.role_id
            ):
                if str(server_id_a) == str(server_id_b.server_id):
                    return True
        return False

    @staticmethod
    def is_crashed(server_id):
        return HelperServers.is_crashed(server_id)

    @staticmethod
    def server_id_authorized_api_key(server_id: str, api_key: ApiKeys) -> bool:
        # TODO
        return ServersController.server_id_authorized(server_id, api_key.user.user_id)
        # There is no view server permission
        # permission_helper.both_have_perm(api_key)

    def set_update(self, server_id, value):
        return self.servers_helper.set_update(server_id, value)

    @staticmethod
    def get_ttl_without_player(server_id):
        return HelperServers.get_ttl_without_player(server_id)

    @staticmethod
    def can_stop_no_players(server_id, time_limit):
        return HelperServers.can_stop_no_players(server_id, time_limit)

    def set_waiting_start(self, server_id, value):
        self.servers_helper.set_waiting_start(server_id, value)

    @staticmethod
    def get_waiting_start(server_id):
        return HelperServers.get_waiting_start(server_id)

    @staticmethod
    def get_update_status(server_id):
        return HelperServers.get_update_status(server_id)

    # **********************************************************************************
    #                                    Servers Helpers Methods
    # **********************************************************************************
    @staticmethod
    def get_banned_players(server_id):
        stats = HelperServers.get_server_stats_by_id(server_id)
        server_path = stats["server_id"]["path"]
        path = os.path.join(server_path, "banned-players.json")

        try:
            with open(
                Helpers.get_os_understandable_path(path), encoding="utf-8"
            ) as file:
                content = file.read()
                file.close()
        except Exception as ex:
            print(ex)
            return None

        return json.loads(content)

    def check_for_old_logs(self):
        servers = HelperServers.get_all_defined_servers()
        for server in servers:
            logs_path = os.path.split(server["log_path"])[0]
            latest_log_file = os.path.split(server["log_path"])[1]
            logs_delete_after = int(server["logs_delete_after"])
            if logs_delete_after == 0:
                continue

            log_files = list(
                filter(lambda val: val != latest_log_file, os.listdir(logs_path))
            )
            for log_file in log_files:
                log_file_path = os.path.join(logs_path, log_file)
                if Helpers.check_file_exists(
                    log_file_path
                ) and Helpers.is_file_older_than_x_days(
                    log_file_path, logs_delete_after
                ):
                    os.remove(log_file_path)
