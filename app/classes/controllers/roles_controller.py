import logging

from app.classes.models.roles import HelperRoles
from app.classes.models.server_permissions import PermissionsServers
from app.classes.shared.helpers import Helpers

logger = logging.getLogger(__name__)


class RolesController:
    def __init__(self, users_helper, roles_helper):
        self.users_helper = users_helper
        self.roles_helper = roles_helper

    @staticmethod
    def get_all_roles():
        return HelperRoles.get_all_roles()

    @staticmethod
    def get_all_role_ids():
        return HelperRoles.get_all_role_ids()

    @staticmethod
    def get_roleid_by_name(role_name):
        return HelperRoles.get_roleid_by_name(role_name)

    @staticmethod
    def get_role(role_id):
        return HelperRoles.get_role(role_id)

    @staticmethod
    def update_role(role_id: str, role_data=None, permissions_mask: str = "00000000"):
        if role_data is None:
            role_data = {}
        base_data = RolesController.get_role_with_servers(role_id)
        up_data = {}
        added_servers = set()
        removed_servers = set()
        for key in role_data:
            if key == "role_id":
                continue
            elif key == "servers":
                added_servers = set(role_data["servers"]).difference(
                    set(base_data["servers"])
                )
                removed_servers = set(base_data["servers"]).difference(
                    set(role_data["servers"])
                )
            elif base_data[key] != role_data[key]:
                up_data[key] = role_data[key]
        up_data["last_update"] = Helpers.get_time_as_string()
        logger.debug(
            f"role: {role_data} +server:{added_servers} -server{removed_servers}"
        )
        for server in added_servers:
            PermissionsServers.get_or_create(role_id, server, permissions_mask)
        for server in base_data["servers"]:
            PermissionsServers.update_role_permission(role_id, server, permissions_mask)
            # TODO: This is horribly inefficient and we should be using bulk queries
            # but im going for functionality at this point
        PermissionsServers.delete_roles_permissions(role_id, removed_servers)
        if up_data:
            HelperRoles.update_role(role_id, up_data)

    @staticmethod
    def add_role(role_name):
        return HelperRoles.add_role(role_name)

    def remove_role(self, role_id):
        role_data = RolesController.get_role_with_servers(role_id)
        PermissionsServers.delete_roles_permissions(role_id, role_data["servers"])
        self.users_helper.remove_roles_from_role_id(role_id)
        return self.roles_helper.remove_role(role_id)

    @staticmethod
    def role_id_exists(role_id):
        return HelperRoles.role_id_exists(role_id)

    @staticmethod
    def get_role_with_servers(role_id):
        role = HelperRoles.get_role(role_id)

        if role:
            server_ids = PermissionsServers.get_server_ids_from_role(role_id)
            role["servers"] = list(server_ids)
            # logger.debug("role: ({}) {}".format(role_id, role))
            return role
        else:
            # logger.debug("role: ({}) {}".format(role_id, {}))
            return {}
