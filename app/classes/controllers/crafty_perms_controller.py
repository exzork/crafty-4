import os
import time
import logging
import sys
import yaml
import asyncio
import shutil
import tempfile
import zipfile
from distutils import dir_util

from app.classes.shared.helpers import helper
from app.classes.shared.console import console

from app.classes.models.crafty_permissions import  crafty_permissions, Enum_Permissions_Crafty

from app.classes.shared.server import Server
from app.classes.minecraft.server_props import ServerProps
from app.classes.minecraft.serverjars import server_jar_obj
from app.classes.minecraft.stats import Stats
from app.classes.models.users import ApiKeys

logger = logging.getLogger(__name__)

class Crafty_Perms_Controller:

    @staticmethod
    def list_defined_crafty_permissions():
        permissions_list = crafty_permissions.get_permissions_list()
        return permissions_list

    @staticmethod
    def get_mask_crafty_permissions(user_id):
        permissions_mask = crafty_permissions.get_crafty_permissions_mask(user_id)
        return permissions_mask

    @staticmethod
    def set_permission(permission_mask, permission_tested: Enum_Permissions_Crafty, value):
        return crafty_permissions.set_permission(permission_mask, permission_tested, value)

    @staticmethod
    def can_create_server(user_id):
        return crafty_permissions.can_add_in_crafty(user_id, Enum_Permissions_Crafty.Server_Creation)

    @staticmethod
    def can_add_user(user_id):
        #TODO: Complete if we need a User Addition limit
        #return crafty_permissions.can_add_in_crafty(user_id, Enum_Permissions_Crafty.User_Config)
        return True

    @staticmethod
    def can_add_role(user_id):
        #TODO: Complete if we need a Role Addition limit
        #return crafty_permissions.can_add_in_crafty(user_id, Enum_Permissions_Crafty.Roles_Config)
        return True

    @staticmethod
    def list_all_crafty_permissions_quantity_limits():
        return crafty_permissions.get_all_permission_quantity_list()

    @staticmethod
    def list_crafty_permissions_quantity_limits(user_id):
        return crafty_permissions.get_permission_quantity_list(user_id)

    @staticmethod
    def get_crafty_permissions_list(user_id):
        permissions_mask = crafty_permissions.get_crafty_permissions_mask(user_id)
        permissions_list = crafty_permissions.get_permissions(permissions_mask)
        return permissions_list

    @staticmethod
    def add_server_creation(user_id):
        return crafty_permissions.add_server_creation(user_id)

    @staticmethod
    def get_api_key_permissions_list(key: ApiKeys):
        return crafty_permissions.get_api_key_permissions_list(key)
