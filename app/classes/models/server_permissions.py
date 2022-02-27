import sys
import logging

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.shared.permission_helper import permission_helper

from app.classes.models.servers import Servers
from app.classes.models.roles import Roles
from app.classes.models.users import User_Roles, users_helper, ApiKeys, Users


logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger('peewee')
peewee_logger.setLevel(logging.INFO)

try:
    from peewee import SqliteDatabase, Model, ForeignKeyField, CharField, CompositeKey, JOIN
    from enum import Enum

except ModuleNotFoundError as e:
    logger.critical(f"Import Error: Unable to load {e.name} module", exc_info=True)
    console.critical(f"Import Error: Unable to load {e.name} module")
    sys.exit(1)

database = SqliteDatabase(helper.db_path, pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 10})


#************************************************************************************************
#                                  Role Servers Class
#************************************************************************************************
class Role_Servers(Model):
    role_id = ForeignKeyField(Roles, backref='role_server')
    server_id = ForeignKeyField(Servers, backref='role_server')
    permissions = CharField(default="00000000")

    class Meta:
        table_name = 'role_servers'
        primary_key = CompositeKey('role_id', 'server_id')
        database = database

#************************************************************************************************
#                                  Servers Permissions Class
#************************************************************************************************
class Enum_Permissions_Server(Enum):
    Commands = 0
    Terminal = 1
    Logs = 2
    Schedule = 3
    Backup = 4
    Files = 5
    Config = 6
    Players = 7

class Permissions_Servers:

    @staticmethod
    def get_or_create(role_id, server, permissions_mask):
        return Role_Servers.get_or_create(role_id=role_id, server_id=server, permissions=permissions_mask)

    @staticmethod
    def get_permissions_list():
        permissions_list = []
        for member in Enum_Permissions_Server.__members__.items():
            permissions_list.append(member[1])
        return permissions_list

    @staticmethod
    def get_permissions(permissions_mask):
        permissions_list = []
        for member in Enum_Permissions_Server.__members__.items():
            if server_permissions.has_permission(permissions_mask, member[1]):
                permissions_list.append(member[1])
        return permissions_list

    @staticmethod
    def has_permission(permission_mask, permission_tested: Enum_Permissions_Server):
        return permission_mask[permission_tested.value] == '1'

    @staticmethod
    def set_permission(permission_mask, permission_tested: Enum_Permissions_Server, value):
        list_perms = list(permission_mask)
        list_perms[permission_tested.value] = str(value)
        permission_mask = ''.join(list_perms)
        return permission_mask

    @staticmethod
    def get_permission(permission_mask, permission_tested: Enum_Permissions_Server):
        return permission_mask[permission_tested.value]

    @staticmethod
    def get_token_permissions(permissions_mask, api_permissions_mask):
        permissions_list = []
        for member in Enum_Permissions_Server.__members__.items():
            if permission_helper.both_have_perm(permissions_mask, api_permissions_mask, member[1]):
                permissions_list.append(member[1])
        return permissions_list


    #************************************************************************************************
    #                                   Role_Servers Methods
    #************************************************************************************************
    @staticmethod
    def get_role_servers_from_role_id(roleid):
        return Role_Servers.select().where(Role_Servers.role_id == roleid)

    @staticmethod
    def get_servers_from_role(role_id):
        return Role_Servers.select().join(Servers, JOIN.INNER).where(Role_Servers.role_id == role_id)

    @staticmethod
    def get_roles_from_server(server_id):
        return Role_Servers.select().join(Roles, JOIN.INNER).where(Role_Servers.server_id == server_id)

    @staticmethod
    def add_role_server(server_id, role_id, rs_permissions="00000000"):
        servers = Role_Servers.insert({Role_Servers.server_id: server_id, Role_Servers.role_id: role_id,
            Role_Servers.permissions: rs_permissions}).execute()
        return servers

    @staticmethod
    def get_permissions_mask(role_id, server_id):
        permissions_mask = ''
        role_server = Role_Servers.select().where(Role_Servers.role_id == role_id).where(Role_Servers.server_id == server_id).get()
        permissions_mask = role_server.permissions
        return permissions_mask

    @staticmethod
    def get_server_roles(server_id):
        role_list = []
        roles = Role_Servers.select().where(Role_Servers.server_id == server_id).execute()
        for role in roles:
            role_list.append(role.role_id)
        return role_list

    @staticmethod
    def get_role_permissions_list(role_id):
        permissions_mask = '00000000'
        role_server = Role_Servers.get_or_none(Role_Servers.role_id == role_id)
        if role_server is not None:
            permissions_mask = role_server.permissions
        permissions_list = server_permissions.get_permissions(permissions_mask)
        return permissions_list

    @staticmethod
    def update_role_permission(role_id, server_id, permissions_mask):
        role_server = Role_Servers.select().where(Role_Servers.role_id == role_id).where(Role_Servers.server_id == server_id).get()
        role_server.permissions = permissions_mask
        Role_Servers.save(role_server)

    @staticmethod
    def delete_roles_permissions(role_id, removed_servers=None):
        if removed_servers is None:
            removed_servers = {}
        return Role_Servers.delete().where(Role_Servers.role_id == role_id).where(Role_Servers.server_id.in_(removed_servers)).execute()

    @staticmethod
    def remove_roles_of_server(server_id):
        with database.atomic():
            return Role_Servers.delete().where(Role_Servers.server_id == server_id).execute()

    @staticmethod
    def get_user_id_permissions_mask(user_id, server_id: str):
        user = users_helper.get_user_model(user_id)
        return server_permissions.get_user_permissions_mask(user, server_id)

    @staticmethod
    def get_user_permissions_mask(user: Users, server_id: str):
        if user.superuser:
            permissions_mask = '1' * len(server_permissions.get_permissions_list())
        else:
            roles_list = users_helper.get_user_roles_id(user.user_id)
            role_server = Role_Servers.select().where(Role_Servers.role_id.in_(roles_list)).where(Role_Servers.server_id == server_id).execute()
            try:
                permissions_mask = role_server[0].permissions
            except IndexError:
                permissions_mask = '0' * len(server_permissions.get_permissions_list())
        return permissions_mask

    @staticmethod
    def get_server_user_list(server_id):
        final_users = []
        server_roles = Role_Servers.select().where(Role_Servers.server_id == server_id)
        # pylint: disable=singleton-comparison
        super_users = Users.select().where(Users.superuser == True)
        for role in server_roles:
            users = User_Roles.select().where(User_Roles.role_id == role.role_id)
            for user in users:
                if user.user_id.user_id not in final_users:
                    final_users.append(user.user_id.user_id)
        for suser in super_users:
            if suser.user_id not in final_users:
                final_users.append(suser.user_id)
        return final_users

    @staticmethod
    def get_user_id_permissions_list(user_id, server_id: str):
        user = users_helper.get_user_model(user_id)
        return server_permissions.get_user_permissions_list(user, server_id)

    @staticmethod
    def get_user_permissions_list(user: Users, server_id: str):
        if user.superuser:
            permissions_list = server_permissions.get_permissions_list()
        else:
            permissions_mask = server_permissions.get_user_permissions_mask(user, server_id)
            permissions_list = server_permissions.get_permissions(permissions_mask)
        return permissions_list

    @staticmethod
    def get_api_key_id_permissions_list(key_id, server_id: str):
        key = ApiKeys.get(ApiKeys.token_id == key_id)
        return server_permissions.get_api_key_permissions_list(key, server_id)

    @staticmethod
    def get_api_key_permissions_list(key: ApiKeys, server_id: str):
        user = key.user
        if user.superuser and key.superuser:
            return server_permissions.get_permissions_list()
        else:
            roles_list = users_helper.get_user_roles_id(user['user_id'])
            role_server = Role_Servers.select().where(Role_Servers.role_id.in_(roles_list)).where(Role_Servers.server_id == server_id).execute()
            user_permissions_mask = role_server[0].permissions
            key_permissions_mask = key.server_permissions
            permissions_mask = permission_helper.combine_masks(user_permissions_mask, key_permissions_mask)
            permissions_list = server_permissions.get_permissions(permissions_mask)
            return permissions_list


server_permissions = Permissions_Servers()
