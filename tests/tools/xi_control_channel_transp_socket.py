import socket
import threading
from threading import Thread

import sys
if sys.version_info[0] < 3:
    import Queue as queue
else:
    import queue as queue

class XiControlChannel_transp_socket:

    def __init__(self, message_sink):
        self.__xi_message_sink = message_sink
        self._send_data_queue = queue.Queue()
        self.__socket = None
        self.__socket_thread = None

    def __del__(self):
        self._listen_on_socket = False
        if (self.__socket):
            self.__socket.close()
            self.__socket_thread.join()

    def stop(self):
        self._listen_on_socket = False
        if (self.__socket):
            self.__socket.close()

    def join(self, timeout):
        if (self.__socket_thread):
            self.__socket_thread.join(timeout)
            return not self.__socket_thread.isAlive()
        return True

    # server behaviour
    def create_listensocket(self):
        # listen on a socket serving as control channel later
        self._listensock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_IP)
        self._listensock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listensock.bind(("127.0.0.1", 0))
        self._listensock.listen(1)
        self._listensock.settimeout(5)
        self._listensock.settimeout(1)

        self.hostaddr, self.port = self._listensock.getsockname()

    def wait_for_connection(self):
        self.__log_prefix = "PR "
        self.__log("Control channel listening on " + str(self._listensock.getsockname()))

        try:
            self.__socket, address = self._listensock.accept()
        except socket.timeout:
            self.__log("ERROR: timeout: Xively Client did not connect to control channel in time")
            raise

        #self._socket_control_channel.setblocking(0)
        self._listensock.close()
        self.__log("Control channel accepted connection: " + str(self.__socket.getsockname()))

        self._listen_on_socket = True
        self.__socket_thread = Thread(target = self.__socket_thread_function)
        self.__socket_thread.start()

    # client behaviour
    def connect(self, host, port):
        self.__log_prefix = "PD "
        self.__log("connecting to " + host + ":" + str(port))
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_IP)
        self.__socket.connect((host, port))

        self._listen_on_socket = True
        self.__socket_thread = Thread(target = self.__socket_thread_function)
        self.__socket_thread.start()

    def send(self, data):
        # thread safe functionality is turned off for now, seems no need for that currently
        if (True or threading.get_ident() == self.__socket_thread.ident):
            self.__socket.sendall(data)
        else:
            self.__log("queuing send")
            self._send_data_queue.put(data)

    def __socket_thread_function(self):
        self.__log("Control channel endpoint thread started: " + threading.current_thread().getName())

        # if threadsafety turned on use non-blocking socket not to make listening block the sending
        self.__socket.setblocking(1)
        self.__socket.settimeout(0.1)

        while self._listen_on_socket:
            try:
                self.__socket.sendall(self._send_data_queue.get(False))
            except queue.Empty as empty:
                pass

            data = ""
            try:
                data = self.__socket.recv(1024)
            except socket.timeout:
                continue
            except socket.error:
                continue
            except Exception as ex_recv:
                self.__log("Exception during receiving data on control channel: " + str(ex_recv))
                break;

            # log("data len = " + str(len(data)) + ", content = " + str(data))

            if data:
                self.__log("Data arrived on control channel: " + str(data))
                self.__xi_message_sink.handle_message(data)
                #self.__handle_incoming_message(data)
            else:
                # recv returned with zero data without timeout -> closed?
                if (self._listen_on_socket):
                    self.__log("WARNING: empty Data arrived, exiting")
                break;
                #pass

        self.__log("Control channel endpoint closed, exiting thread.")
        pass

    def __getLogPrefix(self):
        return "[ " + self.__log_prefix + " transp ] [" + threading.current_thread().getName() + "]: "

    def __log(self, msg):
        print(self.__getLogPrefix() + msg)
