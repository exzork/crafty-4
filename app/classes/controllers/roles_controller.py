import logging

from app.classes.models.roles import roles_helper
from app.classes.models.server_permissions import server_permissions
from app.classes.models.users import users_helper
from app.classes.shared.helpers import helper

logger = logging.getLogger(__name__)

class Roles_Controller:

    @staticmethod
    def get_all_roles():
        return  roles_helper.get_all_roles()

    @staticmethod
    def get_roleid_by_name(role_name):
        return roles_helper.get_roleid_by_name(role_name)

    @staticmethod
    def get_role(role_id):
        return roles_helper.get_role(role_id)


    @staticmethod
    def update_role(role_id: str, role_data = None, permissions_mask: str = "00000000"):
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
                added_servers = role_data['servers'].difference(base_data['servers'])
                removed_servers = base_data['servers'].difference(role_data['servers'])
            elif base_data[key] != role_data[key]:
                up_data[key] = role_data[key]
        up_data['last_update'] = helper.get_time_as_string()
        logger.debug(f"role: {role_data} +server:{added_servers} -server{removed_servers}")
        for server in added_servers:
            server_permissions.get_or_create(role_id, server, permissions_mask)
        for server in base_data['servers']:
            server_permissions.update_role_permission(role_id, server, permissions_mask)
            # TODO: This is horribly inefficient and we should be using bulk queries but im going for functionality at this point
        server_permissions.delete_roles_permissions(role_id, removed_servers)
        if up_data:
            roles_helper.update_role(role_id, up_data)

    @staticmethod
    def add_role(role_name):
        return roles_helper.add_role(role_name)

    @staticmethod
    def remove_role(role_id):
        role_data = Roles_Controller.get_role_with_servers(role_id)
        server_permissions.delete_roles_permissions(role_id, role_data['servers'])
        users_helper.remove_roles_from_role_id(role_id)
        return roles_helper.remove_role(role_id)

    @staticmethod
    def role_id_exists(role_id):
        return roles_helper.role_id_exists(role_id)

    @staticmethod
    def get_role_with_servers(role_id):
        role = roles_helper.get_role(role_id)

        if role:
            servers_query = server_permissions.get_servers_from_role(role_id)
            # TODO: this query needs to be narrower
            servers = set()
            for s in servers_query:
                servers.add(s.server_id.server_id)
            role['servers'] = servers
            #logger.debug("role: ({}) {}".format(role_id, role))
            return role
        else:
            #logger.debug("role: ({}) {}".format(role_id, {}))
            return {}
