import json

import tornado.websocket
from app.classes.shared.console import console
from app.classes.web.websocket_helper import websocket_helper


class WebSocketHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        websocket_helper.addClient(self)
        console.debug('Opened WebSocket connection')
        websocket_helper.broadcast('client_joined', {})

    def on_message(self, rawMessage):

        console.debug('Got message from WebSocket connection {}'.format(rawMessage))
        message = json.loads(rawMessage)
        console.debug('Type: {}, Data: {}'.format(message['type'], message['data']))

    def on_close(self):
        websocket_helper.removeClient(self)
        console.debug('Closed WebSocket connection')

