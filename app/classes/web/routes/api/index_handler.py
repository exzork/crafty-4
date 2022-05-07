from app.classes.web.base_api_handler import BaseApiHandler

WIKI_API_LINK = "https://wiki.craftycontrol.com/en/4/docs/API V2"


class ApiIndexHandler(BaseApiHandler):
    def get(self):
        self.finish_json(
            200,
            {
                "status": "ok",
                "data": {
                    "version": self.controller.helper.get_version_string(),
                    "message": f"Please see the API documentation at {WIKI_API_LINK}",
                },
            },
        )
