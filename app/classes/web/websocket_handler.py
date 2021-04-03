import json

import tornado.websocket
from app.classes.shared.console import console
from app.classes.shared.models import Users, db_helper
from app.classes.web.websocket_helper import websocket_helper


class SocketHandler(tornado.websocket.WebSocketHandler):

    def initialize(self, controller=None, tasks_manager=None, translator=None):
        self.controller = controller
        self.tasks_manager = tasks_manager
        self.translator = translator

    def get_remote_ip(self):
        remote_ip = self.request.headers.get("X-Real-IP") or \
                    self.request.headers.get("X-Forwarded-For") or \
                    self.request.remote_ip
        return remote_ip

    def check_auth(self):
        user_data_cookie_raw = self.get_secure_cookie('user_data')

        if user_data_cookie_raw and user_data_cookie_raw.decode('utf-8'):
            user_data_cookie = user_data_cookie_raw.decode('utf-8')
            user_id = json.loads(user_data_cookie)['user_id']
            query = Users.select().where(Users.user_id == user_id)
            if query.exists():
                return True
        return False


    def open(self):
        if self.check_auth():
            self.handle()
        else:
            websocket_helper.send_message(self, 'notification', 'Not authenticated for WebSocket connection')
            self.close()
            db_helper.add_to_audit_log_raw('unknown', 0, 0, 'Someone tried to connect via WebSocket without proper authentication', self.get_remote_ip())
            websocket_helper.broadcast('notification', 'Someone tried to connect via WebSocket without proper authentication')

    def handle(self):
        
        websocket_helper.addClient(self)
        console.debug('Opened WebSocket connection')
        # websocket_helper.broadcast('notification', 'New client connected')

    def on_message(self, rawMessage):

        console.debug('Got message from WebSocket connection {}'.format(rawMessage))
        message = json.loads(rawMessage)
        console.debug('Event Type: {}, Data: {}'.format(message['event'], message['data']))

    def on_close(self):
        websocket_helper.removeClient(self)
        console.debug('Closed WebSocket connection')
        # websocket_helper.broadcast('notification', 'Client disconnected')

