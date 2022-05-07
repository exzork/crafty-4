import json
import logging

from jsonschema import ValidationError, validate
from app.classes.models.crafty_permissions import EnumPermissionsCrafty
from app.classes.models.roles import HelperRoles
from app.classes.models.users import HelperUsers
from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)


class ApiUsersUserIndexHandler(BaseApiHandler):
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
            res_user = user
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
            res_user = self.controller.users.get_user_by_id(user_id)
            if not res_user:
                return self.finish_json(
                    404,
                    {
                        "status": "error",
                        "error": "USER_NOT_FOUND",
                    },
                )

        # Remove password and valid_tokens_from from the response
        # as those should never be sent out to the client.
        res_user.pop("password", None)
        res_user.pop("valid_tokens_from", None)
        res_user["roles"] = list(
            map(HelperRoles.get_role, res_user.get("roles", set()))
        )

        self.finish_json(
            200,
            {"status": "ok", "data": res_user},
        )

    def delete(self, user_id: str):
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

        if (user_id in ["@me", user["user_id"]]) and self.helper.get_setting(
            "allow_self_delete", False
        ):
            self.controller.users.remove_user(user["user_id"])
        elif EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                },
            )
        else:
            # has User_Config permission
            self.controller.users.remove_user(user_id)

        self.finish_json(
            200,
            {"status": "ok"},
        )

    def patch(self, user_id: str):
        user_patch_schema = {
            "type": "object",
            "properties": {
                **self.controller.users.user_jsonschema_props,
            },
            "anyOf": [
                # Require at least one property
                {"required": [name]}
                for name in [
                    "username",
                    "password",
                    "email",
                    "enabled",
                    "lang",
                    "superuser",
                    "permissions",
                    "roles",
                    "hints",
                ]
            ],
            "additionalProperties": False,
        }
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            exec_user_crafty_permissions,
            _,
            superuser,
            user,
        ) = auth_data

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, user_patch_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        if user_id == "@me":
            user_id = user["user_id"]

        if (
            EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions
            and str(user["user_id"]) != str(user_id)
        ):
            # If doesn't have perm can't edit other users
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                },
            )

        if data.get("username", None) is not None:
            if data["username"].lower() in ["system", ""]:
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_USERNAME"}
                )
            if self.controller.users.get_id_by_name(data["username"]) is not None:
                return self.finish_json(
                    400, {"status": "error", "error": "USER_EXISTS"}
                )

        if data.get("superuser", None) is not None:
            if str(user["user_id"]) == str(user_id):
                # Checks if user is trying to change super user status of self.
                # We don't want that.
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_SUPERUSER_MODIFY"}
                )
            if not superuser:
                # The user is not superuser so they can't change the superuser status
                data.pop("superuser")

        if data.get("permissions", None) is not None:
            if str(user["user_id"]) == str(user_id):
                # Checks if user is trying to change permissions of self.
                # We don't want that.
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_PERMISSIONS_MODIFY"}
                )
            if EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
                # Checks if user is trying to change permissions of someone
                # else without User Config permission. We don't want that.
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_PERMISSIONS_MODIFY"}
                )

        if data.get("roles", None) is not None:
            if str(user["user_id"]) == str(user_id):
                # Checks if user is trying to change roles of self.
                # We don't want that.
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_ROLES_MODIFY"}
                )
            if EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
                # Checks if user is trying to change roles of someone
                # else without User Config permission. We don't want that.
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_ROLES_MODIFY"}
                )

        # TODO: make this more efficient
        # TODO: add permissions and roles because I forgot
        user_obj = HelperUsers.get_user_model(user_id)

        self.controller.management.add_to_audit_log(
            user["user_id"],
            (
                f"edited user {user_obj.username} (UID: {user_id})"
                f"with roles {user_obj.roles}"
            ),
            server_id=0,
            source_ip=self.get_remote_ip(),
        )

        for key in data:
            # If we don't validate the input there could be security issues
            setattr(user_obj, key, data[key])
        user_obj.save()

        return self.finish_json(200, {"status": "ok"})
