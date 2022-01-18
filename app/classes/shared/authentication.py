import logging
import time
from typing import Optional, Dict, Any, Tuple

import jwt
from jwt import PyJWTError

from app.classes.models.users import users_helper, ApiKeys
from app.classes.shared.helpers import helper

logger = logging.getLogger(__name__)


class Authentication:
    def __init__(self):
        self.secret = "my secret"
        self.secret = helper.get_setting('apikey_secret', None)

        if self.secret is None or self.secret == 'random':
            self.secret = helper.random_string_generator(64)

    @staticmethod
    def generate(user_id, extra=None):
        if extra is None:
            extra = {}
        return jwt.encode(
            {
                'user_id': user_id,
                'iat': int(time.time()),
                **extra
            },
            authentication.secret,
            algorithm="HS256"
        )

    @staticmethod
    def read(token):
        return jwt.decode(token, authentication.secret, algorithms=["HS256"])

    @staticmethod
    def check_no_iat(token) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, authentication.secret, algorithms=["HS256"])
        except PyJWTError as error:
            logger.debug("Error while checking JWT token: ", exc_info=error)
            return None

    @staticmethod
    def check(token) -> Optional[Tuple[Optional[ApiKeys], Dict[str, Any], Dict[str, Any]]]:
        try:
            data = jwt.decode(token, authentication.secret, algorithms=["HS256"])
        except PyJWTError as error:
            logger.debug("Error while checking JWT token: ", exc_info=error)
            return None
        iat: int = data['iat']
        key: Optional[ApiKeys] = None
        if 'token_id' in data:
            key_id = data['token_id']
            key = users_helper.get_user_api_key(key_id)
            if key is None:
                return None
        user_id: str = data['user_id']
        user = users_helper.get_user(user_id)
        # TODO: Have a cache or something so we don't constantly have to query the database
        if int(user.get('valid_tokens_from').timestamp()) < iat:
            # Success!
            return key, data, user
        else:
            return None

    @staticmethod
    def check_bool(token) -> bool:
        return authentication.check(token) is not None


authentication = Authentication()
