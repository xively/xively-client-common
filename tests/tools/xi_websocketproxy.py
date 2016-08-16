import time
import socket
import threading
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
from tools.xi_tornadothread import XiTornadoThread


class XiWebSocketProxyServer:

    wsClient = None
    tcpClient = None

    host = ""
    port = ""

    def __init__(self):

        self.server = None
        self.address = None

        XiWebSocketProxyServer.wsClient = None
        XiWebSocketProxyServer.tcpClient = None


    def start(self,host,port,certfile=None,keyfile=None):

        XiTornadoThread.start()

        XiWebSocketProxyServer.host = host
        XiWebSocketProxyServer.port = port

        sockets = tornado.netutil.bind_sockets( 0, 'localhost', socket.AF_INET )
        self.address = sockets[0].getsockname()
        self.app = tornado.web.Application( [ ( r'/mqtt' , XiWebSocketProxyWebSocket ) ] )

        if certfile == None :

            self.server = tornado.httpserver.HTTPServer( self.app )

        else:

            self.server = tornado.httpserver.HTTPServer( self.app , ssl_options = {
                "certfile": certfile,
                "keyfile": keyfile,
            })

        self.server.add_sockets( sockets )


    def _stop_impl(self):

        if XiWebSocketProxyServer.wsClient is not None:
            XiWebSocketProxyServer.wsClient.get_websocket_protocol()._abort()

        XiTornadoThread.stop()

        self.server.stop( )

    def stop(self):

        tornado.ioloop.IOLoop.instance().add_callback(callback=lambda: self._stop_impl())


class XiWebSocketProxyWebSocket(tornado.websocket.WebSocketHandler):


    def check_origin(self, origin):

        return True


    def open(self):

        XiWebSocketProxyServer.wsClient = self
        XiWebSocketProxyServer.tcpClient = XiWebSocketProxyTcpClient()
        XiWebSocketProxyServer.tcpClient.start( XiWebSocketProxyServer.host , XiWebSocketProxyServer.port )

        # hold server thread until connect until tcp client is ready to send/receive
        while XiWebSocketProxyServer.tcpClient.active == 0:
            pass


    def on_close(self):

        if XiWebSocketProxyServer.tcpClient is not None:

            XiWebSocketProxyServer.tcpClient.stop()
            XiWebSocketProxyServer.tcpClient = None
            XiWebSocketProxyServer.wsClient = None


    def on_message(self, message):

        if XiWebSocketProxyServer.tcpClient is not None:

            XiWebSocketProxyServer.tcpClient.socket.send( message )

    def _message_impl(self,message):
        self.write_message( message, True )

    def message(self,message):
        tornado.ioloop.IOLoop.instance().add_callback(callback=lambda: self._message_impl(message))


class XiWebSocketProxyTcpClient:


    def startrecv(self):

        self.active = 1
        while self.active == 1 :

            try:

                reply = self.socket.recv( 1024 )

            except Exception as e:

                reply = b""

            # check end of file
            if reply != b"" :

                if XiWebSocketProxyServer.wsClient is not None:
                    XiWebSocketProxyServer.wsClient.message(reply)

            else :

                self.active = 0

        self.closed = 1


    def start( self , host , port ):

        # connect socket

        try :
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM )
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR , 1 )
            self.socket.connect( ( host , port ) )
            self.closed = 0

            thread = threading.Thread( target = self.startrecv , args = [ ] )
            thread.start( )

        except Exception:
            self.active = 0
            self.closed = 1

    def stop(self):

        self.active = 0
        self.socket.close()

