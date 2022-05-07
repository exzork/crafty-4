from app.classes.web.base_api_handler import BaseApiHandler


class ApiRolesRoleIndexHandler(BaseApiHandler):
    def get(self, role_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            superuser,
            _,
        ) = auth_data

        if not superuser:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        # TODO: permissions
        self.finish_json(
            200,
            {"status": "ok", "data": self.controller.roles.get_role(role_id)},
        )
