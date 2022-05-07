from app.classes.models.server_permissions import PermissionsServers
from app.classes.web.base_api_handler import BaseApiHandler


class ApiRolesRoleServersHandler(BaseApiHandler):
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

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": PermissionsServers.get_server_ids_from_role(role_id),
            },
        )
