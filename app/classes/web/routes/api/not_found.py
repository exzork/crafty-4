from app.classes.web.base_api_handler import BaseApiHandler


class ApiNotFoundHandler(BaseApiHandler):
    def get(self, page: str):
        self.finish_json(
            404,
            {"status": "error", "error": "API_HANDLER_NOT_FOUND", "page": page},
        )
