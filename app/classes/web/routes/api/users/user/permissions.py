import logging
import typing as t

from app.classes.models.crafty_permissions import (
    EnumPermissionsCrafty,
    PermissionsCrafty,
)
from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)


SERVER_CREATION: t.Final[str] = EnumPermissionsCrafty.SERVER_CREATION.name
USER_CONFIG: t.Final[str] = EnumPermissionsCrafty.USER_CONFIG.name
ROLES_CONFIG: t.Final[str] = EnumPermissionsCrafty.ROLES_CONFIG.name


class ApiUsersUserPermissionsHandler(BaseApiHandler):
    def get(self, user_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            exec_user_crafty_permissions,
            _,
            _,
            user,
        ) = auth_data

        if user_id in ["@me", user["user_id"]]:
            user_id = user["user_id"]
            res_data = PermissionsCrafty.get_user_crafty(user_id)
        elif EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                },
            )
        else:
            # has User_Config permission and isn't viewing self
            res_data = PermissionsCrafty.get_user_crafty_optional(user_id)
            if res_data is None:
                return self.finish_json(
                    404,
                    {
                        "status": "error",
                        "error": "USER_NOT_FOUND",
                    },
                )

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": {
                    "permissions": res_data.permissions,
                    "counters": {
                        SERVER_CREATION: res_data.created_server,
                        USER_CONFIG: res_data.created_user,
                        ROLES_CONFIG: res_data.created_role,
                    },
                    "limits": {
                        SERVER_CREATION: res_data.limit_server_creation,
                        USER_CONFIG: res_data.limit_user_creation,
                        ROLES_CONFIG: res_data.limit_role_creation,
                    },
                },
            },
        )
