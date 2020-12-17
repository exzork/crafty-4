import json

import tornado.websocket
from app.classes.shared.console import console
from app.classes.shared.models import db_helper


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    connections = set()
    host_stats = db_helper.get_latest_hosts_stats()

    def open(self):
        self.connections.add(self)
        console.debug('Opened WebSocket connection')
        self.broadcast('client_joined', {
            'foo': 'bar',
        })

    def on_message(self, message):
        # broadcast
        #         for client in self.connections:
        #             client.write_message(message)

        # send message to client this message was sent by
        # self.write_message

        console.debug('Got message from WebSocket connection {}'.format(message))

    def on_close(self):
        self.connections.remove(self)
        console.debug('Closed WebSocket connection')

    def broadcast(self, message_type: str, data):
        print(str(json.dumps({'type': message_type, 'data': data})))
        message = str(json.dumps({'type': message_type, 'data': data}))
        for client in self.connections:
            client.write_message(message)
