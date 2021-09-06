import os
import sys
import logging
import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.shared.models import db_helper, server_permissions, Enum_Permissions_Server

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
        user_crafty = db_helper.get_User_Crafty(user_id)
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
        user_crafty = db_helper.get_User_Crafty(user_id)
        quantity_list = {
            Enum_Permissions_Crafty.Server_Creation.name: user_crafty.limit_server_creation,
            Enum_Permissions_Crafty.User_Config.name: user_crafty.limit_user_creation,
            Enum_Permissions_Crafty.Roles_Config.name: user_crafty.limit_role_creation,
        }
        return quantity_list

crafty_permissions = Permissions_Crafty()