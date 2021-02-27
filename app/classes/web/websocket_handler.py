import json

import tornado.websocket
from app.classes.shared.console import console
from app.classes.web.websocket_helper import websocket_helper


class WebSocketHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        websocket_helper.addClient(self)
        console.debug('Opened WebSocket connection')
        websocket_helper.broadcast('notification', 'New client connected')

    def on_message(self, rawMessage):

        console.debug('Got message from WebSocket connection {}'.format(rawMessage))
        message = json.loads(rawMessage)
        console.debug('Event Type: {}, Data: {}'.format(message['event'], message['data']))

    def on_close(self):
        websocket_helper.removeClient(self)
        console.debug('Closed WebSocket connection')
        websocket_helper.broadcast('notification', 'Client disconnected')

