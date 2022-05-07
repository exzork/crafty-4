import logging
import typing
from enum import Enum
from peewee import (
    ForeignKeyField,
    CharField,
    IntegerField,
    DoesNotExist,
)

from app.classes.models.base_model import BaseModel
from app.classes.models.users import Users, ApiKeys, HelperUsers
from app.classes.shared.permission_helper import PermissionHelper

logger = logging.getLogger(__name__)

# **********************************************************************************
#                                  User_Crafty Class
# **********************************************************************************
class UserCrafty(BaseModel):
    user_id = ForeignKeyField(Users, backref="users_crafty")
    permissions = CharField(default="00000000")
    limit_server_creation = IntegerField(default=-1)
    limit_user_creation = IntegerField(default=0)
    limit_role_creation = IntegerField(default=0)
    created_server = IntegerField(default=0)
    created_user = IntegerField(default=0)
    created_role = IntegerField(default=0)

    class Meta:
        table_name = "user_crafty"


# **********************************************************************************
#                                  Crafty Permissions Class
# **********************************************************************************
class EnumPermissionsCrafty(Enum):
    SERVER_CREATION = 0
    USER_CONFIG = 1
    ROLES_CONFIG = 2


class PermissionsCrafty:
    # **********************************************************************************
    #                                  Crafty Permissions Methods
    # **********************************************************************************
    @staticmethod
    def get_permissions_list():
        permissions_list: typing.List[EnumPermissionsCrafty] = []
        for member in EnumPermissionsCrafty.__members__.items():
            permissions_list.append(member[1])
        return permissions_list

    @staticmethod
    def get_permissions(permissions_mask):
        permissions_list: typing.List[EnumPermissionsCrafty] = []
        for member in EnumPermissionsCrafty.__members__.items():
            if PermissionsCrafty.has_permission(permissions_mask, member[1]):
                permissions_list.append(member[1])
        return permissions_list

    @staticmethod
    def has_permission(
        permission_mask: typing.Mapping[int, str],
        permission_tested: EnumPermissionsCrafty,
    ):
        result = False
        if permission_mask[permission_tested.value] == "1":
            result = True
        return result

    @staticmethod
    def set_permission(
        permission_mask, permission_tested: EnumPermissionsCrafty, value
    ):
        lst = list(permission_mask)
        lst[permission_tested.value] = str(value)
        permission_mask = "".join(lst)
        return permission_mask

    @staticmethod
    def get_permission(permission_mask, permission_tested: EnumPermissionsCrafty):
        return permission_mask[permission_tested.value]

    @staticmethod
    def get_crafty_permissions_mask(user_id):
        permissions_mask = ""
        user_crafty = PermissionsCrafty.get_user_crafty(user_id)
        permissions_mask = user_crafty.permissions
        return permissions_mask

    @staticmethod
    def get_all_permission_quantity_list():
        quantity_list = {
            EnumPermissionsCrafty.SERVER_CREATION.name: -1,
            EnumPermissionsCrafty.USER_CONFIG.name: -1,
            EnumPermissionsCrafty.ROLES_CONFIG.name: -1,
        }
        return quantity_list

    @staticmethod
    def get_permission_quantity_list(user_id):
        user_crafty = PermissionsCrafty.get_user_crafty(user_id)
        quantity_list = {
            EnumPermissionsCrafty.SERVER_CREATION.name: user_crafty.limit_server_creation,  # pylint: disable=line-too-long
            EnumPermissionsCrafty.USER_CONFIG.name: user_crafty.limit_user_creation,
            EnumPermissionsCrafty.ROLES_CONFIG.name: user_crafty.limit_role_creation,
        }
        return quantity_list

    # **********************************************************************************
    #                                   User_Crafty Methods
    # **********************************************************************************
    @staticmethod
    def get_user_crafty(user_id):
        try:
            user_crafty = UserCrafty.select().where(UserCrafty.user_id == user_id).get()
        except DoesNotExist:
            user_crafty = UserCrafty.insert(
                {
                    UserCrafty.user_id: user_id,
                    UserCrafty.permissions: "000",
                    UserCrafty.limit_server_creation: 0,
                    UserCrafty.limit_user_creation: 0,
                    UserCrafty.limit_role_creation: 0,
                    UserCrafty.created_server: 0,
                    UserCrafty.created_user: 0,
                    UserCrafty.created_role: 0,
                }
            ).execute()
            user_crafty = PermissionsCrafty.get_user_crafty(user_id)
        return user_crafty

    @staticmethod
    def add_user_crafty(user_id, uc_permissions):
        user_crafty = UserCrafty.insert(
            {UserCrafty.user_id: user_id, UserCrafty.permissions: uc_permissions}
        ).execute()
        return user_crafty

    @staticmethod
    def add_or_update_user(
        user_id,
        permissions_mask,
        limit_server_creation,
        limit_user_creation,
        limit_role_creation,
    ):
        try:
            user_crafty = UserCrafty.select().where(UserCrafty.user_id == user_id).get()
            user_crafty.permissions = permissions_mask
            user_crafty.limit_server_creation = limit_server_creation
            user_crafty.limit_user_creation = limit_user_creation
            user_crafty.limit_role_creation = limit_role_creation
            UserCrafty.save(user_crafty)
        except:
            UserCrafty.insert(
                {
                    UserCrafty.user_id: user_id,
                    UserCrafty.permissions: permissions_mask,
                    UserCrafty.limit_server_creation: limit_server_creation,
                    UserCrafty.limit_user_creation: limit_user_creation,
                    UserCrafty.limit_role_creation: limit_role_creation,
                }
            ).execute()

    @staticmethod
    def get_created_quantity_list(user_id):
        user_crafty = PermissionsCrafty.get_user_crafty(user_id)
        quantity_list = {
            EnumPermissionsCrafty.SERVER_CREATION.name: user_crafty.created_server,
            EnumPermissionsCrafty.USER_CONFIG.name: user_crafty.created_user,
            EnumPermissionsCrafty.ROLES_CONFIG.name: user_crafty.created_role,
        }
        return quantity_list

    @staticmethod
    def get_crafty_limit_value(user_id, permission):
        quantity_list = PermissionsCrafty.get_permission_quantity_list(user_id)
        return quantity_list[permission]

    @staticmethod
    def can_add_in_crafty(user_id, permission):
        user_crafty = PermissionsCrafty.get_user_crafty(user_id)
        can = PermissionsCrafty.has_permission(user_crafty.permissions, permission)
        limit_list = PermissionsCrafty.get_permission_quantity_list(user_id)
        quantity_list = PermissionsCrafty.get_created_quantity_list(user_id)
        return can and (
            (quantity_list[permission.name] < limit_list[permission.name])
            or limit_list[permission.name] == -1
        )

    @staticmethod
    def add_server_creation(user_id):
        """Increase the "Server Creation" counter for this user

        Args:
            user_id (int): The modifiable user's ID

        Returns:
            int: The new count of servers created by this user
        """
        user_crafty = PermissionsCrafty.get_user_crafty(user_id)
        user_crafty.created_server += 1
        UserCrafty.save(user_crafty)
        return user_crafty.created_server

    @staticmethod
    def get_api_key_permissions_list(key: ApiKeys):
        user = HelperUsers.get_user(key.user_id)
        if user["superuser"] and key.superuser:
            return PermissionsCrafty.get_permissions_list()
        else:
            if user["superuser"]:
                user_permissions_mask = "111"
            else:
                user_permissions_mask = PermissionsCrafty.get_crafty_permissions_mask(
                    user["user_id"]
                )
            key_permissions_mask: str = key.crafty_permissions
            permissions_mask = PermissionHelper.combine_masks(
                user_permissions_mask, key_permissions_mask
            )
            permissions_list = PermissionsCrafty.get_permissions(permissions_mask)
            return permissions_list
