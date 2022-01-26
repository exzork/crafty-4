import logging

from app.classes.models.server_permissions import  server_permissions, Enum_Permissions_Server
from app.classes.models.users import users_helper, ApiKeys
from app.classes.models.roles import roles_helper
from app.classes.models.servers import servers_helper

from app.classes.shared.main_models import db_helper

logger = logging.getLogger(__name__)

class Server_Perms_Controller:

    @staticmethod
    def get_server_user_list(server_id):
        return server_permissions.get_server_user_list(server_id)

    @staticmethod
    def list_defined_permissions():
        permissions_list = server_permissions.get_permissions_list()
        return permissions_list

    @staticmethod
    def get_mask_permissions(role_id, server_id):
        permissions_mask = server_permissions.get_permissions_mask(role_id, server_id)
        return permissions_mask

    @staticmethod
    def get_role_permissions(role_id):
        permissions_list = server_permissions.get_role_permissions_list(role_id)
        return permissions_list

    @staticmethod
    def add_role_server(server_id, role_id, rs_permissions="00000000"):
        return server_permissions.add_role_server(server_id, role_id, rs_permissions)

    @staticmethod
    def get_server_roles(server_id):
        return server_permissions.get_server_roles(server_id)

    @staticmethod
    def backup_role_swap(old_server_id, new_server_id):
        role_list = server_permissions.get_server_roles(old_server_id)
        for role in role_list:
            server_permissions.add_role_server(
                new_server_id, role.role_id,
                server_permissions.get_permissions_mask(int(role.role_id), int(old_server_id)))
            #server_permissions.add_role_server(new_server_id, role.role_id, '00001000')

    #************************************************************************************************
    #                                   Servers Permissions Methods
    #************************************************************************************************
    @staticmethod
    def get_permissions_mask(role_id, server_id):
        return server_permissions.get_permissions_mask(role_id, server_id)

    @staticmethod
    def set_permission(permission_mask, permission_tested: Enum_Permissions_Server, value):
        return server_permissions.set_permission(permission_mask, permission_tested, value)

    @staticmethod
    def get_role_permissions_list(role_id):
        return server_permissions.get_role_permissions_list(role_id)

    @staticmethod
    def get_user_id_permissions_list(user_id: str, server_id: str):
        return server_permissions.get_user_id_permissions_list(user_id, server_id)

    @staticmethod
    def get_api_key_id_permissions_list(key_id: str, server_id: str):
        key = users_helper.get_user_api_key(key_id)
        return server_permissions.get_api_key_permissions_list(key, server_id)

    @staticmethod
    def get_api_key_permissions_list(key: ApiKeys, server_id: str):
        return server_permissions.get_api_key_permissions_list(key, server_id)

    @staticmethod
    def get_authorized_servers_stats_from_roles(user_id):
        user_roles = users_helper.get_user_roles_id(user_id)
        roles_list = []
        role_server = []
        authorized_servers = []
        server_data = []

        for u in user_roles:
            roles_list.append(roles_helper.get_role(u.role_id))

        for r in roles_list:
            role_test = server_permissions.get_role_servers_from_role_id(r.get('role_id'))
            for t in role_test:
                role_server.append(t)

        for s in role_server:
            authorized_servers.append(servers_helper.get_server_data_by_id(s.server_id))

        for s in authorized_servers:
            latest = servers_helper.get_latest_server_stats(s.get('server_id'))
            server_data.append({'server_data': s, "stats": db_helper.return_rows(latest)[0]})
        return server_data
