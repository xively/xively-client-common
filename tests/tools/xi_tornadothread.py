import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import threading

class XiTornadoThread( ):

    started = False

    @classmethod
    def stop(cls):

        cls.started = False
        tornado.ioloop.IOLoop.instance( ).stop( )

    @classmethod
    def startThread(cls):

        cls.started = True
        tornado.ioloop.IOLoop.instance( ).start( )

    @classmethod
    def start(cls):

        if tornado.ioloop.IOLoop.instance()._running == False :
            threading.Thread( target = XiTornadoThread.startThread , args = [ ] ).start( )
        else :
            cls.started = True