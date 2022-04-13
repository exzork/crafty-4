import logging
from typing import Optional

from app.classes.models.users import helper_users
from app.classes.models.crafty_permissions import (
    Permissions_Crafty,
    Enum_Permissions_Crafty,
)

logger = logging.getLogger(__name__)


class Users_Controller:
    def __init__(self, helper, users_helper, authentication):
        self.helper = helper
        self.users_helper = users_helper
        self.authentication = authentication

    # **********************************************************************************
    #                                   Users Methods
    # **********************************************************************************
    @staticmethod
    def get_all_users():
        return helper_users.get_all_users()

    @staticmethod
    def get_id_by_name(username):
        return helper_users.get_user_id_by_name(username)

    @staticmethod
    def get_user_lang_by_id(user_id):
        return helper_users.get_user_lang_by_id(user_id)

    @staticmethod
    def get_user_by_id(user_id):
        return helper_users.get_user(user_id)

    @staticmethod
    def update_server_order(user_id, user_server_order):
        helper_users.update_server_order(user_id, user_server_order)

    @staticmethod
    def get_server_order(user_id):
        return helper_users.get_server_order(user_id)

    @staticmethod
    def user_query(user_id):
        return helper_users.user_query(user_id)

    @staticmethod
    def set_support_path(user_id, support_path):
        helper_users.set_support_path(user_id, support_path)

    def update_user(self, user_id: str, user_data=None, user_crafty_data=None):
        if user_crafty_data is None:
            user_crafty_data = {}
        if user_data is None:
            user_data = {}
        base_data = helper_users.get_user(user_id)
        up_data = {}
        added_roles = set()
        removed_roles = set()
        for key in user_data:
            if key == "user_id":
                continue
            elif key == "roles":
                added_roles = user_data["roles"].difference(base_data["roles"])
                removed_roles = base_data["roles"].difference(user_data["roles"])
            elif key == "password":
                if user_data["password"] is not None and user_data["password"] != "":
                    up_data["password"] = self.helper.encode_pass(user_data["password"])
            elif base_data[key] != user_data[key]:
                up_data[key] = user_data[key]
        up_data["last_update"] = self.helper.get_time_as_string()
        up_data["lang"] = user_data["lang"]
        up_data["hints"] = user_data["hints"]
        logger.debug(f"user: {user_data} +role:{added_roles} -role:{removed_roles}")
        for role in added_roles:
            helper_users.get_or_create(user_id=user_id, role_id=role)
        permissions_mask = user_crafty_data.get("permissions_mask", "000")

        if "server_quantity" in user_crafty_data:
            limit_server_creation = user_crafty_data["server_quantity"][
                Enum_Permissions_Crafty.Server_Creation.name
            ]

            limit_user_creation = user_crafty_data["server_quantity"][
                Enum_Permissions_Crafty.User_Config.name
            ]
            limit_role_creation = user_crafty_data["server_quantity"][
                Enum_Permissions_Crafty.Roles_Config.name
            ]
        else:
            limit_server_creation = 0
            limit_user_creation = 0
            limit_role_creation = 0

        Permissions_Crafty.add_or_update_user(
            user_id,
            permissions_mask,
            limit_server_creation,
            limit_user_creation,
            limit_role_creation,
        )

        self.users_helper.delete_user_roles(user_id, removed_roles)

        self.users_helper.update_user(user_id, up_data)

    def add_user(
        self,
        username,
        password,
        email="default@example.com",
        enabled: bool = True,
        superuser: bool = False,
    ):
        return self.users_helper.add_user(
            username,
            password=password,
            email=email,
            enabled=enabled,
            superuser=superuser,
        )

    @staticmethod
    def add_rawpass_user(
        username,
        password,
        email="default@example.com",
        enabled: bool = True,
        superuser: bool = False,
    ):
        return helper_users.add_rawpass_user(
            username,
            password=password,
            email=email,
            enabled=enabled,
            superuser=superuser,
        )

    def remove_user(self, user_id):
        return self.users_helper.remove_user(user_id)

    @staticmethod
    def user_id_exists(user_id):
        return helper_users.user_id_exists(user_id)

    @staticmethod
    def set_prepare(user_id):
        return helper_users.set_prepare(user_id)

    @staticmethod
    def stop_prepare(user_id):
        return helper_users.stop_prepare(user_id)

    def get_user_id_by_api_token(self, token: str) -> str:
        token_data = self.authentication.check_no_iat(token)
        return token_data["user_id"]

    def get_user_by_api_token(self, token: str):
        _, _, user = self.authentication.check(token)
        return user

    def get_api_key_by_token(self, token: str):
        key, _, _ = self.authentication.check(token)
        return key

    # **********************************************************************************
    #                                   User Roles Methods
    # **********************************************************************************

    @staticmethod
    def get_user_roles_id(user_id):
        return helper_users.get_user_roles_id(user_id)

    @staticmethod
    def get_user_roles_names(user_id):
        return helper_users.get_user_roles_names(user_id)

    def add_role_to_user(self, user_id, role_id):
        return self.users_helper.add_role_to_user(user_id, role_id)

    def add_user_roles(self, user):
        return self.users_helper.add_user_roles(user)

    @staticmethod
    def user_role_query(user_id):
        return helper_users.user_role_query(user_id)

    # **********************************************************************************
    #                                   Api Keys Methods
    # **********************************************************************************

    @staticmethod
    def get_user_api_keys(user_id: str):
        return helper_users.get_user_api_keys(user_id)

    @staticmethod
    def get_user_api_key(key_id: str):
        return helper_users.get_user_api_key(key_id)

    def add_user_api_key(
        self,
        name: str,
        user_id: str,
        superuser: bool = False,
        server_permissions_mask: Optional[str] = None,
        crafty_permissions_mask: Optional[str] = None,
    ):
        return self.users_helper.add_user_api_key(
            name, user_id, superuser, server_permissions_mask, crafty_permissions_mask
        )

    def delete_user_api_keys(self, user_id: str):
        return self.users_helper.delete_user_api_keys(user_id)

    def delete_user_api_key(self, key_id: str):
        return self.users_helper.delete_user_api_key(key_id)
