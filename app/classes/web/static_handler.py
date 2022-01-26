from typing import ( Optional )
import tornado.web

class CustomStaticHandler(tornado.web.StaticFileHandler):
    def validate_absolute_path(self, root: str, absolute_path: str) -> Optional[str]:
        try:
            return super().validate_absolute_path(root, absolute_path)
        except tornado.web.HTTPError as error:
            if 'HTTP 404: Not Found' in str(error):
                self.set_status(404)
                self.finish({'error':'NOT_FOUND', 'info':'The requested resource was not found on the server'})
