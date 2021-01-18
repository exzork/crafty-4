import json

import tornado.websocket
from app.classes.shared.console import console
from app.classes.shared.models import db_helper


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    connections = set()

    def open(self):
        self.connections.add(self)
        console.debug('Opened WebSocket connection')
        self.broadcast('client_joined', {
            'foo': 'bar',
        })

    def on_message(self, rawMessage):
        # broadcast
        #         for client in self.connections:
        #             client.write_message(message)

        # send message to client this message was sent by
        # self.write_message

        console.debug('Got message from WebSocket connection {}'.format(rawMessage))
        message = json.loads(rawMessage)
        console.debug('Type: {}, Data: {}'.format(message['type'], message['data']))

    def on_close(self):
        self.connections.remove(self)
        console.debug('Closed WebSocket connection')

    def broadcast(self, message_type: str, data):
        console.debug('Sending: ' + str(json.dumps({'type': message_type, 'data': data})))
        message = str(json.dumps({'type': message_type, 'data': data}))
        for client in self.connections:
            client.write_message(message)
