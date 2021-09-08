import os
import sys
import logging
import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.models.servers import Servers
from app.classes.models.roles import Roles
from app.classes.models.users import users_helper

logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger('peewee')
peewee_logger.setLevel(logging.INFO)

try:
    from peewee import *
    from playhouse.shortcuts import model_to_dict
    from enum import Enum
    import yaml

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e.name), exc_info=True)
    console.critical("Import Error: Unable to load {} module".format(e.name))
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
        result = False
        if permission_mask[permission_tested.value] == '1':
            result = True
        return result

    @staticmethod
    def set_permission(permission_mask, permission_tested: Enum_Permissions_Server, value):
        list_perms = list(permission_mask)
        list_perms[permission_tested.value] = str(value)
        permission_mask = ''.join(list_perms)
        return permission_mask

    @staticmethod
    def get_permission(permission_mask, permission_tested: Enum_Permissions_Server):
        return permission_mask[permission_tested.value]

        
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
    def add_role_server(server_id, role_id, rs_permissions="00000000"):
        servers = Role_Servers.insert({Role_Servers.server_id: server_id, Role_Servers.role_id: role_id, Role_Servers.permissions: rs_permissions}).execute()
        return servers
        
    @staticmethod
    def get_permissions_mask(role_id, server_id):
        permissions_mask = ''
        role_server = Role_Servers.select().where(Role_Servers.role_id == role_id).where(Role_Servers.server_id == server_id).execute()
        permissions_mask = role_server.permissions
        return permissions_mask

    @staticmethod
    def get_role_permissions_list(role_id):
        permissions_mask = ''
        role_server = Role_Servers.select().where(Role_Servers.role_id == role_id).execute()
        permissions_mask = role_server[0].permissions
        permissions_list = server_permissions.get_permissions(permissions_mask)
        return permissions_list

    @staticmethod
    def update_role_permission(role_id, server_id, permissions_mask):
        role_server = Role_Servers.select().where(Role_Servers.role_id == role_id).where(Role_Servers.server_id == server_id).get()
        role_server.permissions = permissions_mask
        Role_Servers.save(role_server)

    @staticmethod
    def delete_roles_permissions(role_id, removed_servers={}):
        return Role_Servers.delete().where(Role_Servers.role_id == role_id).where(Role_Servers.server_id.in_(removed_servers)).execute()

    @staticmethod
    def get_user_permissions_list(user_id, server_id):
        permissions_mask = ''
        permissions_list = []

        user = users_helper.get_user(user_id)
        if user['superuser'] == True:
            permissions_list = server_permissions.get_permissions_list()
        else:
            roles_list = users_helper.get_user_roles_id(user_id)
            role_server = Role_Servers.select().where(Role_Servers.role_id.in_(roles_list)).where(Role_Servers.server_id == int(server_id)).execute()
            permissions_mask = role_server[0].permissions
            permissions_list = server_permissions.get_permissions(permissions_mask)
        return permissions_list
        
server_permissions = Permissions_Servers()