import json
import tornado.ioloop
import tornado.websocket
import tornado.httpserver
import tornado.netutil

from tools.xi_mock_broker.mqtt_messages import MQTTMessage
from tools.xi_tornadothread import XiTornadoThread

class XiWebSocketServerWebSocket(tornado.websocket.WebSocketHandler):


    def check_origin(self, origin):

        return True


    def open(self):

        XiWebSocketServer.wsClient = self
        XiWebSocketServer.connected = True


    def on_close(self):

        XiWebSocketServer.wsClient = None
        XiWebSocketServer.connected = False


    def on_message(self, message):

        argsobj = json.loads( message )

        if argsobj['command'] == "REJECTED" :

            XiWebSocketServer.testerObject.on_connect_reject_tunnel( argsobj )

        elif argsobj['command'] == "CONNECTED" :

            XiWebSocketServer.testerObject.on_connect_finish( 0 )

        elif argsobj['command'] == "DISCONNECTED" :

            XiWebSocketServer.testerObject.on_disconnect( 0 )

        elif argsobj['command'] == "SUBSCRIBED" :

            XiWebSocketServer.testerObject.on_subscribe_finish( [0] )

        elif argsobj['command'] == "UNSUBSCRIBED" :

            XiWebSocketServer.testerObject.on_subscribe_finish( argsobj[ 'qos' ] )

        elif argsobj['command'] == "PUBLISHED" :

            #XiWebSocketServer.testerObject.on_publish_finish( argsobj[ 'message' ] , argsobj[ 'qos' ] )
            XiWebSocketServer.testerObject.on_publish_finish( 0 )

        elif argsobj['command'] == "MESSAGE" :

            # convert payload to bytearray
            bytes = bytearray( )
            bytes.extend(map(ord, argsobj[ 'payload' ]))

            # create MQTT message
            message = MQTTMessage()
            message.topic = argsobj['topic']
            message.payload = bytes
            message.qos = 0

            XiWebSocketServer.testerObject.on_message_received( argsobj[ 'topic' ] , message )


class XiWebSocketServer:

    wsClient = None
    connected = False
    testerObject = None


    def __init__(self,testerObject):

        self.server = None
        self.address = None

        XiWebSocketServer.wsClient = None
        XiWebSocketServer.connected = False
        XiWebSocketServer.testerObject = testerObject


    def start(self):

        XiTornadoThread.start()

        sockets = tornado.netutil.bind_sockets( 0, 'localhost' )
        self.address = sockets[0].getsockname()
        self.app = tornado.web.Application( [ ( r'/' , XiWebSocketServerWebSocket ) ] )
        self.server = tornado.httpserver.HTTPServer( self.app )
        self.server.add_sockets( sockets )


    def stop(self):

        self.server.stop( )

    def message(self,message):

        if XiWebSocketServer.wsClient != None :
            XiWebSocketServer.wsClient.write_message( message , False )