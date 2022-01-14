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

from app.classes.models.users import Users, users_helper
from app.classes.models.crafty_permissions import crafty_permissions, Enum_Permissions_Crafty
from app.classes.models.management import management_helper

logger = logging.getLogger(__name__)

class Users_Controller:
    
    #************************************************************************************************
    #                                   Users Methods
    #************************************************************************************************
    @staticmethod
    def get_all_users():
        return users_helper.get_all_users()

    @staticmethod
    def get_id_by_name(username):
        return users_helper.get_user_id_by_name(username)

    @staticmethod
    def get_user_by_api_token(token: str):
        return users_helper.get_user_by_api_token(token)

    @staticmethod
    def get_user_lang_by_id(user_id):
        return users_helper.get_user_lang_by_id(user_id)

    @staticmethod
    def get_user_by_id(user_id):
        return users_helper.get_user(user_id)

    @staticmethod
    def user_query(user_id):
        return users_helper.user_query(user_id)

    @staticmethod
    def set_support_path(user_id, support_path):
        users_helper.set_support_path(user_id, support_path)

    @staticmethod
    def update_user(user_id, user_data={}, user_crafty_data={}):
        base_data = users_helper.get_user(user_id)
        up_data = {}
        added_roles = set()
        removed_roles = set()
        removed_servers = set()
        for key in user_data:
            if key == "user_id":
                continue
            elif key == "roles":
                added_roles = user_data['roles'].difference(base_data['roles'])
                removed_roles = base_data['roles'].difference(user_data['roles'])
            elif key == "regen_api":
                if user_data['regen_api']:
                    up_data['api_token'] = management_helper.new_api_token()
            elif key == "password":
                if user_data['password'] is not None and user_data['password'] != "":
                    up_data['password'] = helper.encode_pass(user_data['password'])
            elif base_data[key] != user_data[key]:
                up_data[key] = user_data[key]
        up_data['last_update'] = helper.get_time_as_string()
        up_data['lang'] = user_data['lang']
        logger.debug("user: {} +role:{} -role:{}".format(user_data, added_roles, removed_roles))
        for role in added_roles:
            users_helper.get_or_create(user_id=user_id, role_id=role)
            # TODO: This is horribly inefficient and we should be using bulk queries but im going for functionality at this point

        for key in user_crafty_data:
            if key == "permissions_mask":
                permissions_mask = user_crafty_data['permissions_mask']
            if key == "server_quantity":
                limit_server_creation = user_crafty_data['server_quantity'][Enum_Permissions_Crafty.Server_Creation.name]
                limit_user_creation = user_crafty_data['server_quantity'][Enum_Permissions_Crafty.User_Config.name]
                limit_role_creation = user_crafty_data['server_quantity'][Enum_Permissions_Crafty.Roles_Config.name]
            else:
                limit_server_creation = 0
                limit_user_creation = 0
                limit_role_creation = 0

            crafty_permissions.add_or_update_user(user_id, permissions_mask, limit_server_creation, limit_user_creation, limit_role_creation)

            users_helper.delete_user_roles(user_id, removed_roles)

        users_helper.update_user(user_id, up_data)

    @staticmethod
    def add_user(username, password=None, email="default@example.com", api_token=None, enabled=True, superuser=False):
        return users_helper.add_user(username, password=password, email=email, api_token=api_token, enabled=enabled, superuser=superuser)

    @staticmethod
    def remove_user(user_id):
        return users_helper.remove_user(user_id)

    @staticmethod
    def user_id_exists(user_id):
        return users_helper.user_id_exists(user_id)

    #************************************************************************************************
    #                                   User Roles Methods
    #************************************************************************************************
        
    @staticmethod
    def get_user_roles_id(user_id):
        return users_helper.get_user_roles_id(user_id)

    @staticmethod
    def get_user_roles_names(user_id):
        return users_helper.get_user_roles_names(user_id)

    @staticmethod
    def add_role_to_user(user_id, role_id):
        return users_helper.add_role_to_user(user_id, role_id)

    @staticmethod
    def add_user_roles(user):
        return users_helper.add_user_roles(user)
        
    @staticmethod
    def user_role_query(user_id):
        return users_helper.user_role_query(user_id)
