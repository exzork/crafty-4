import logging

from app.classes.models.roles import helper_roles
from app.classes.models.server_permissions import Permissions_Servers
from app.classes.shared.helpers import Helpers

logger = logging.getLogger(__name__)


class Roles_Controller:
    def __init__(self, users_helper):
        self.users_helper = users_helper
    @staticmethod
    def get_all_roles():
        return helper_roles.get_all_roles()

    @staticmethod
    def get_roleid_by_name(role_name):
        return helper_roles.get_roleid_by_name(role_name)

    @staticmethod
    def get_role(role_id):
        return helper_roles.get_role(role_id)

    @staticmethod
    def update_role(role_id: str, role_data=None, permissions_mask: str = "00000000"):
        if role_data is None:
            role_data = {}
        base_data = Roles_Controller.get_role_with_servers(role_id)
        up_data = {}
        added_servers = set()
        removed_servers = set()
        for key in role_data:
            if key == "role_id":
                continue
            elif key == "servers":
                added_servers = role_data["servers"].difference(base_data["servers"])
                removed_servers = base_data["servers"].difference(role_data["servers"])
            elif base_data[key] != role_data[key]:
                up_data[key] = role_data[key]
        up_data["last_update"] = Helpers.get_time_as_string()
        logger.debug(
            f"role: {role_data} +server:{added_servers} -server{removed_servers}"
        )
        for server in added_servers:
            Permissions_Servers.get_or_create(role_id, server, permissions_mask)
        for server in base_data["servers"]:
            Permissions_Servers.update_role_permission(role_id, server, permissions_mask)
            # TODO: This is horribly inefficient and we should be using bulk queries
            # but im going for functionality at this point
        Permissions_Servers.delete_roles_permissions(role_id, removed_servers)
        if up_data:
            helper_roles.update_role(role_id, up_data)

    @staticmethod
    def add_role(role_name):
        return helper_roles.add_role(role_name)

    def remove_role(self, role_id):
        role_data = Roles_Controller.get_role_with_servers(role_id)
        Permissions_Servers.delete_roles_permissions(role_id, role_data["servers"])
        self.users_helper.remove_roles_from_role_id(role_id)
        return helper_roles.remove_role(role_id)

    @staticmethod
    def role_id_exists(role_id):
        return helper_roles.role_id_exists(role_id)

    @staticmethod
    def get_role_with_servers(role_id):
        role = helper_roles.get_role(role_id)

        if role:
            servers_query = Permissions_Servers.get_servers_from_role(role_id)
            # TODO: this query needs to be narrower
            servers = set()
            for s in servers_query:
                servers.add(s.server_id.server_id)
            role["servers"] = servers
            # logger.debug("role: ({}) {}".format(role_id, role))
            return role
        else:
            # logger.debug("role: ({}) {}".format(role_id, {}))
            return {}
