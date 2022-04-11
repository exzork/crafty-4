import logging

from app.classes.models.crafty_permissions import (
    Permissions_Crafty,
    Enum_Permissions_Crafty,
)
from app.classes.models.users import ApiKeys

logger = logging.getLogger(__name__)


class Crafty_Perms_Controller:
    @staticmethod
    def list_defined_crafty_permissions():
        permissions_list = Permissions_Crafty.get_permissions_list()
        return permissions_list

    @staticmethod
    def get_mask_crafty_permissions(user_id):
        permissions_mask = Permissions_Crafty.get_crafty_permissions_mask(user_id)
        return permissions_mask

    @staticmethod
    def set_permission(
        permission_mask, permission_tested: Enum_Permissions_Crafty, value
    ):
        return Permissions_Crafty.set_permission(
            permission_mask, permission_tested, value
        )

    @staticmethod
    def can_create_server(user_id):
        return Permissions_Crafty.can_add_in_crafty(
            user_id, Enum_Permissions_Crafty.Server_Creation
        )

    @staticmethod
    def can_add_user():  # Add back argument 'user_id' when you work on this
        return True
        # TODO: Complete if we need a User Addition limit
        # return crafty_permissions.can_add_in_crafty(
        #     user_id, Enum_Permissions_Crafty.User_Config
        # )

    @staticmethod
    def can_add_role():  # Add back argument 'user_id' when you work on this
        return True
        # TODO: Complete if we need a Role Addition limit
        # return crafty_permissions.can_add_in_crafty(
        #     user_id, Enum_Permissions_Crafty.Roles_Config
        # )

    @staticmethod
    def list_all_crafty_permissions_quantity_limits():
        return Permissions_Crafty.get_all_permission_quantity_list()

    @staticmethod
    def list_crafty_permissions_quantity_limits(user_id):
        return Permissions_Crafty.get_permission_quantity_list(user_id)

    @staticmethod
    def get_crafty_permissions_list(user_id):
        permissions_mask = Permissions_Crafty.get_crafty_permissions_mask(user_id)
        permissions_list = Permissions_Crafty.get_permissions(permissions_mask)
        return permissions_list

    @staticmethod
    def add_server_creation(user_id):
        return Permissions_Crafty.add_server_creation(user_id)

    @staticmethod
    def get_api_key_permissions_list(key: ApiKeys):
        return Permissions_Crafty.get_api_key_permissions_list(key)
