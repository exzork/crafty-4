from app.classes.web.routes.api.auth.invalidate_tokens import (
    ApiAuthInvalidateTokensHandler,
)
from app.classes.web.routes.api.auth.login import ApiAuthLoginHandler
from app.classes.web.routes.api.servers.index import ApiServersIndexHandler
from app.classes.web.routes.api.servers.server.action import (
    ApiServersServerActionHandler,
)
from app.classes.web.routes.api.servers.server.index import ApiServersServerIndexHandler
from app.classes.web.routes.api.servers.server.logs import ApiServersServerLogsHandler
from app.classes.web.routes.api.servers.server.public import (
    ApiServersServerPublicHandler,
)
from app.classes.web.routes.api.servers.server.stats import ApiServersServerStatsHandler
from app.classes.web.routes.api.servers.server.users import ApiServersServerUsersHandler
from app.classes.web.routes.api.users.index import ApiUsersIndexHandler
from app.classes.web.routes.api.users.user.index import ApiUsersUserIndexHandler
from app.classes.web.routes.api.users.user.pfp import ApiUsersUserPfpHandler
from app.classes.web.routes.api.users.user.public import ApiUsersUserPublicHandler


def api_handlers(handler_args):
    return [
        # Auth routes
        (r"/api/v2/auth/login", ApiAuthLoginHandler, handler_args),
        (
            r"/api/v2/auth/invalidate_tokens",
            ApiAuthInvalidateTokensHandler,
            handler_args,
        ),
        # User routes
        (r"/api/v2/users", ApiUsersIndexHandler, handler_args),
        (r"/api/v2/users/([a-z0-9_]+)", ApiUsersUserIndexHandler, handler_args),
        (r"/api/v2/users/(@me)", ApiUsersUserIndexHandler, handler_args),
        (r"/api/v2/users/([a-z0-9_]+)/pfp", ApiUsersUserPfpHandler, handler_args),
        (r"/api/v2/users/(@me)/pfp", ApiUsersUserPfpHandler, handler_args),
        (r"/api/v2/users/([a-z0-9_]+)/public", ApiUsersUserPublicHandler, handler_args),
        (r"/api/v2/users/(@me)/public", ApiUsersUserPublicHandler, handler_args),
        # Server routes
        (r"/api/v2/servers", ApiServersIndexHandler, handler_args),
        (r"/api/v2/servers/([0-9]+)", ApiServersServerIndexHandler, handler_args),
        (r"/api/v2/servers/([0-9]+)/stats", ApiServersServerStatsHandler, handler_args),
        (
            r"/api/v2/servers/([0-9]+)/action/([a-z_]+)",
            ApiServersServerActionHandler,
            handler_args,
        ),
        (r"/api/v2/servers/([0-9]+)/logs", ApiServersServerLogsHandler, handler_args),
        (r"/api/v2/servers/([0-9]+)/users", ApiServersServerUsersHandler, handler_args),
        (
            r"/api/v2/servers/([0-9]+)/public",
            ApiServersServerPublicHandler,
            handler_args,
        ),
    ]
