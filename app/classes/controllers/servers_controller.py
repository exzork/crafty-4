import os
import logging
import json

from app.classes.controllers.roles_controller import Roles_Controller
from app.classes.models.servers import servers_helper
from app.classes.models.users import users_helper, ApiKeys
from app.classes.models.server_permissions import (
    server_permissions,
    Enum_Permissions_Server,
)
from app.classes.shared.helpers import helper
from app.classes.shared.main_models import db_helper

logger = logging.getLogger(__name__)


class Servers_Controller:

    # ************************************************************************************************
    #                                   Generic Servers Methods
    # ************************************************************************************************
    @staticmethod
    def create_server(
        name: str,
        server_uuid: str,
        server_dir: str,
        backup_path: str,
        server_command: str,
        server_file: str,
        server_log_file: str,
        server_stop: str,
        server_type: str,
        server_port=25565,
    ):
        return servers_helper.create_server(
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
        )

    @staticmethod
    def get_server_obj(server_id):
        return servers_helper.get_server_obj(server_id)

    @staticmethod
    def update_server(server_obj):
        return servers_helper.update_server(server_obj)

    @staticmethod
    def set_download(server_id):
        return servers_helper.set_download(server_id)

    @staticmethod
    def finish_download(server_id):
        return servers_helper.finish_download(server_id)

    @staticmethod
    def get_download_status(server_id):
        return servers_helper.get_download_status(server_id)

    @staticmethod
    def remove_server(server_id):
        roles_list = server_permissions.get_roles_from_server(server_id)
        for role in roles_list:
            role_id = role.role_id
            role_data = Roles_Controller.get_role_with_servers(role_id)
            role_data["servers"] = {server_id}
            server_permissions.delete_roles_permissions(role_id, role_data["servers"])
        server_permissions.remove_roles_of_server(server_id)
        servers_helper.remove_server(server_id)

    @staticmethod
    def get_server_data_by_id(server_id):
        return servers_helper.get_server_data_by_id(server_id)

    # ************************************************************************************************
    #                                     Servers Methods
    # ************************************************************************************************
    @staticmethod
    def get_all_defined_servers():
        return servers_helper.get_all_defined_servers()

    @staticmethod
    def get_authorized_servers(user_id):
        server_data = []
        user_roles = users_helper.user_role_query(user_id)
        for us in user_roles:
            role_servers = server_permissions.get_role_servers_from_role_id(us.role_id)
            for role in role_servers:
                server_data.append(servers_helper.get_server_data_by_id(role.server_id))

        return server_data

    @staticmethod
    def get_all_servers_stats():
        return servers_helper.get_all_servers_stats()

    @staticmethod
    def get_authorized_servers_stats_api_key(api_key: ApiKeys):
        server_data = []
        authorized_servers = Servers_Controller.get_authorized_servers(
            api_key.user.user_id
        )

        for s in authorized_servers:
            latest = servers_helper.get_latest_server_stats(s.get("server_id"))
            key_permissions = server_permissions.get_api_key_permissions_list(
                api_key, s.get("server_id")
            )
            if Enum_Permissions_Server.Commands in key_permissions:
                user_command_permission = True
            else:
                user_command_permission = False
            server_data.append(
                {
                    "server_data": s,
                    "stats": db_helper.return_rows(latest)[0],
                    "user_command_permission": user_command_permission,
                }
            )
        return server_data

    @staticmethod
    def get_authorized_servers_stats(user_id):
        server_data = []
        authorized_servers = Servers_Controller.get_authorized_servers(user_id)

        for s in authorized_servers:
            latest = servers_helper.get_latest_server_stats(s.get("server_id"))
            # TODO
            user_permissions = server_permissions.get_user_id_permissions_list(
                user_id, s.get("server_id")
            )
            if Enum_Permissions_Server.Commands in user_permissions:
                user_command_permission = True
            else:
                user_command_permission = False
            server_data.append(
                {
                    "server_data": s,
                    "stats": db_helper.return_rows(latest)[0],
                    "user_command_permission": user_command_permission,
                }
            )

        return server_data

    @staticmethod
    def get_server_friendly_name(server_id):
        return servers_helper.get_server_friendly_name(server_id)

    # ************************************************************************************************
    #                                    Servers_Stats Methods
    # ************************************************************************************************
    @staticmethod
    def get_server_stats_by_id(server_id):
        return servers_helper.get_server_stats_by_id(server_id)

    @staticmethod
    def server_id_exists(server_id):
        return servers_helper.server_id_exists(server_id)

    @staticmethod
    def get_server_type_by_id(server_id):
        return servers_helper.get_server_type_by_id(server_id)

    @staticmethod
    def server_id_authorized(server_id_a, user_id):
        user_roles = users_helper.user_role_query(user_id)
        for role in user_roles:
            for server_id_b in server_permissions.get_role_servers_from_role_id(
                role.role_id
            ):
                if str(server_id_a) == str(server_id_b.server_id):
                    return True
        return False

    @staticmethod
    def is_crashed(server_id):
        return servers_helper.is_crashed(server_id)

    @staticmethod
    def server_id_authorized_api_key(server_id: str, api_key: ApiKeys) -> bool:
        # TODO
        return Servers_Controller.server_id_authorized(server_id, api_key.user.user_id)
        # There is no view server permission
        # permission_helper.both_have_perm(api_key)

    @staticmethod
    def set_update(server_id, value):
        return servers_helper.set_update(server_id, value)

    @staticmethod
    def get_TTL_without_player(server_id):
        return servers_helper.get_TTL_without_player(server_id)

    @staticmethod
    def can_stop_no_players(server_id, time_limit):
        return servers_helper.can_stop_no_players(server_id, time_limit)

    @staticmethod
    def set_waiting_start(server_id, value):
        servers_helper.set_waiting_start(server_id, value)

    @staticmethod
    def get_waiting_start(server_id):
        return servers_helper.get_waiting_start(server_id)

    @staticmethod
    def get_update_status(server_id):
        return servers_helper.get_update_status(server_id)

    # ************************************************************************************************
    #                                    Servers Helpers Methods
    # ************************************************************************************************
    @staticmethod
    def get_banned_players(server_id):
        stats = servers_helper.get_server_stats_by_id(server_id)
        server_path = stats["server_id"]["path"]
        path = os.path.join(server_path, "banned-players.json")

        try:
            with open(
                helper.get_os_understandable_path(path), encoding="utf-8"
            ) as file:
                content = file.read()
                file.close()
        except Exception as ex:
            print(ex)
            return None

        return json.loads(content)

    def check_for_old_logs(self):
        servers = servers_helper.get_all_defined_servers()
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
                if helper.check_file_exists(
                    log_file_path
                ) and helper.is_file_older_than_x_days(
                    log_file_path, logs_delete_after
                ):
                    os.remove(log_file_path)
