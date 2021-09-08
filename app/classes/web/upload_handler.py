import tornado.options
import tornado.web
import tornado.httpserver
from tornado.options import options
from app.classes.models.server_permissions import Enum_Permissions_Server
from app.classes.shared.helpers import helper
from app.classes.web.websocket_helper import websocket_helper
from app.classes.shared.console import console
import logging
import os
import json
import time

logger = logging.getLogger(__name__)

# Class&Function Defination
MAX_STREAMED_SIZE = 1024 * 1024 * 1024

@tornado.web.stream_request_body
class UploadHandler(tornado.web.RequestHandler):
    def prepare(self):
        self.do_upload = True
        user_data = json.loads(self.get_secure_cookie('user_data'))
        user_id = user_data['user_id']

        server_id = self.request.headers.get('X-ServerId', None)

        if user_id is None:
            logger.warning('User ID not found in upload handler call')
            console.warning('User ID not found in upload handler call')
            self.do_upload = False
        
        if server_id is None:
            logger.warning('Server ID not found in upload handler call')
            console.warning('Server ID not found in upload handler call')
            self.do_upload = False

        user_permissions = self.controller.server_permissions.get_user_permissions_list(user_id, server_id)
        if Enum_Permissions_Server.Files not in user_permissions:
            logger.warning(f'User {user_id} tried to upload a file to {server_id} without permissions!')
            console.warning(f'User {user_id} tried to upload a file to {server_id} without permissions!')
            self.do_upload = False

        path = self.request.headers.get('X-Path', None)
        filename = self.request.headers.get('X-FileName', None)
        full_path = os.path.join(path, filename)

        if not helper.in_path(self.controller.servers.get_server_data_by_id(server_id)['path'], full_path):
            print(user_id, server_id, self.controller.servers.get_server_data_by_id(server_id)['path'], full_path)
            logger.warning(f'User {user_id} tried to upload a file to {server_id} but the path is not inside of the server!')
            console.warning(f'User {user_id} tried to upload a file to {server_id} but the path is not inside of the server!')
            self.do_upload = False
        
        if self.do_upload:
            try:
                self.f = open(full_path, "wb")
            except Exception as e:
                logger.error("Upload failed with error: {}".format(e))
                self.do_upload = False
        # If max_body_size is not set, you cannot upload files > 100MB
        self.request.connection.set_max_body_size(MAX_STREAMED_SIZE)

    def post(self):
        logger.info("Upload completed")
        files_left = int(self.request.headers.get('X-Files-Left', None))
        
        if self.do_upload:
            time.sleep(5)
            if files_left == 0:
                websocket_helper.broadcast('close_upload_box', 'success')
            self.finish('success') # Nope, I'm sending "success"
            self.f.close()
        else:
            time.sleep(5)
            if files_left == 0:
                websocket_helper.broadcast('close_upload_box', 'error')
            self.finish('error')

    def data_received(self, data):
        if self.do_upload:
            self.f.write(data)
