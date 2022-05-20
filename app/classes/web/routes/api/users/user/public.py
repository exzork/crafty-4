import logging
from app.classes.models.roles import HelperRoles
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
            public_user = user
        else:
            public_user = self.controller.users.get_user_by_id(user_id)

        public_user = {key: public_user.get(key) for key in PUBLIC_USER_ATTRS}

        public_user["roles"] = list(
            map(HelperRoles.get_role, public_user.get("roles", set()))
        )

        self.finish_json(
            200,
            {"status": "ok", "data": public_user},
        )
