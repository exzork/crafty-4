import logging
from app.classes.models.roles import helper_roles
from app.classes.models.users import PUBLIC_USER_ATTRS
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)


class ApiUsersUserPublicHandler(BaseApiHandler):
    def get(self, user_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            _,
            user,
        ) = auth_data

        if user_id == "@me":
            user_id = user["user_id"]
            res_user = user

        res_user = {key: getattr(res_user, key) for key in PUBLIC_USER_ATTRS}

        res_user["roles"] = list(
            map(helper_roles.get_role, res_user.get("roles", set()))
        )

        self.finish_json(
            200,
            {"status": "ok", "data": res_user},
        )
