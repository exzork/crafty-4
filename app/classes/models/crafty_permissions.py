import os
import sys
import logging
import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.models.users import Users

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
#                                  User_Crafty Class
#************************************************************************************************
class User_Crafty(Model):
    user_id = ForeignKeyField(Users, backref='users_crafty')
    permissions = CharField(default="00000000")
    limit_server_creation = IntegerField(default=-1)
    limit_user_creation = IntegerField(default=0)
    limit_role_creation = IntegerField(default=0)
    created_server = IntegerField(default=0)
    created_user = IntegerField(default=0)
    created_role = IntegerField(default=0)

    class Meta:
        table_name = 'user_crafty'
        database = database

#************************************************************************************************
#                                  Crafty Permissions Class
#************************************************************************************************
class Enum_Permissions_Crafty(Enum):
    Server_Creation = 0
    User_Config = 1
    Roles_Config = 2

class Permissions_Crafty:

    #************************************************************************************************
    #                                  Crafty Permissions Methods
    #************************************************************************************************
    @staticmethod
    def get_permissions_list():
        permissions_list = []
        for member in Enum_Permissions_Crafty.__members__.items():
            permissions_list.append(member[1])
        return permissions_list

    @staticmethod
    def get_permissions(permissions_mask):
        permissions_list = []
        for member in Enum_Permissions_Crafty.__members__.items():
            if crafty_permissions.has_permission(permissions_mask, member[1]):
                permissions_list.append(member[1])
        return permissions_list

    @staticmethod
    def has_permission(permission_mask, permission_tested: Enum_Permissions_Crafty):
        result = False
        if permission_mask[permission_tested.value] == '1':
            result = True
        return result

    @staticmethod
    def set_permission(permission_mask, permission_tested: Enum_Permissions_Crafty, value):
        l = list(permission_mask)
        l[permission_tested.value] = str(value)
        permission_mask = ''.join(l)
        return permission_mask

    @staticmethod
    def get_permission(permission_mask, permission_tested: Enum_Permissions_Crafty):
        return permission_mask[permission_tested.value]

    @staticmethod
    def get_crafty_permissions_mask(user_id):
        permissions_mask = ''
        user_crafty = crafty_permissions.get_User_Crafty(user_id)
        permissions_mask = user_crafty.permissions
        return permissions_mask

    @staticmethod
    def get_all_permission_quantity_list():
        quantity_list = {
            Enum_Permissions_Crafty.Server_Creation.name: -1,
            Enum_Permissions_Crafty.User_Config.name: -1,
            Enum_Permissions_Crafty.Roles_Config.name: -1,
        }
        return quantity_list

    @staticmethod
    def get_permission_quantity_list(user_id):
        user_crafty = crafty_permissions.get_User_Crafty(user_id)
        quantity_list = {
            Enum_Permissions_Crafty.Server_Creation.name: user_crafty.limit_server_creation,
            Enum_Permissions_Crafty.User_Config.name: user_crafty.limit_user_creation,
            Enum_Permissions_Crafty.Roles_Config.name: user_crafty.limit_role_creation,
        }
        return quantity_list

    #************************************************************************************************
    #                                   User_Crafty Methods
    #************************************************************************************************
    @staticmethod
    def get_User_Crafty(user_id):
        try:
            user_crafty = User_Crafty.select().where(User_Crafty.user_id == user_id).get()
        except User_Crafty.DoesNotExist:
            user_crafty = User_Crafty.insert({
                User_Crafty.user_id: user_id,
                User_Crafty.permissions: "000",
                User_Crafty.limit_server_creation: 0,
                User_Crafty.limit_user_creation: 0,
                User_Crafty.limit_role_creation: 0,
                User_Crafty.created_server: 0,
                User_Crafty.created_user: 0,
                User_Crafty.created_role: 0,
            }).execute()
            user_crafty = crafty_permissions.get_User_Crafty(user_id)
        return user_crafty

    @staticmethod
    def add_user_crafty(user_id, uc_permissions):
        user_crafty = User_Crafty.insert({User_Crafty.user_id: user_id, User_Crafty.permissions: uc_permissions}).execute()
        return user_crafty

    @staticmethod
    def add_or_update_user(user_id, permissions_mask, limit_server_creation, limit_user_creation, limit_role_creation):
        try:
            user_crafty = User_Crafty.select().where(User_Crafty.user_id == user_id).get()
            user_crafty.permissions = permissions_mask
            user_crafty.limit_server_creation = limit_server_creation
            user_crafty.limit_user_creation = limit_user_creation
            user_crafty.limit_role_creation = limit_role_creation
            User_Crafty.save(user_crafty)
        except:
            User_Crafty.insert({
                User_Crafty.user_id: user_id,
                User_Crafty.permissions: permissions_mask,
                User_Crafty.limit_server_creation: limit_server_creation,
                User_Crafty.limit_user_creation: limit_user_creation,
                User_Crafty.limit_role_creation: limit_role_creation
            }).execute()

    @staticmethod
    def get_created_quantity_list(user_id):
        user_crafty = crafty_permissions.get_User_Crafty(user_id)
        quantity_list = {
            Enum_Permissions_Crafty.Server_Creation.name: user_crafty.created_server,
            Enum_Permissions_Crafty.User_Config.name: user_crafty.created_user,
            Enum_Permissions_Crafty.Roles_Config.name: user_crafty.created_role,
        }
        return quantity_list

    @staticmethod
    def get_crafty_limit_value(user_id, permission):
        user_crafty = crafty_permissions.get_User_Crafty(user_id)
        quantity_list = crafty_permissions.get_permission_quantity_list(user_id)
        return quantity_list[permission]

    @staticmethod
    def can_add_in_crafty(user_id, permission):
        user_crafty = crafty_permissions.get_User_Crafty(user_id)
        can = crafty_permissions.has_permission(user_crafty.permissions, permission)
        limit_list = crafty_permissions.get_permission_quantity_list(user_id)
        quantity_list = crafty_permissions.get_created_quantity_list(user_id)
        return can and ((quantity_list[permission.name] < limit_list[permission.name]) or limit_list[permission.name] == -1 )

    @staticmethod
    def add_server_creation(user_id):
        user_crafty = crafty_permissions.get_User_Crafty(user_id)
        user_crafty.created_server += 1
        User_Crafty.save(user_crafty)
        return user_crafty.created_server

crafty_permissions = Permissions_Crafty()