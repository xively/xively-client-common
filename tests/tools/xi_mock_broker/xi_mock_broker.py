
# Copyright (c) 2012-2015 Xively
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v1.0
# and Eclipse Distribution License v1.0 which accompany this distribution.
#
# The Eclipse Public License is available at
#    http://www.eclipse.org/legal/epl-v10.html
# and the Eclipse Distribution License is available at
#   http://www.eclipse.org/org/documents/edl-v10.php.
#
# Contributors:
#    Roger Light <roger@atchoo.org> - initial API and implementation

"""
This is an MQTT v3.1.1 fake (mock) broker module, developed from Roger Light's MQTT client. This broker serves
testing purposes.
"""

import errno
import platform
import select
import socket
import traceback

from enum import Enum
from tools.xi_mock_broker.mqtt_codec import MQTTCodec
from tools.xi_mock_broker.mqtt_messages import *  # FIXME - don't import everything
from tools.xi_websocketproxy import XiWebSocketProxyServer

HAVE_SSL = True
try:
    import ssl
    cert_reqs = ssl.CERT_OPTIONAL
    tls_version = ssl.PROTOCOL_TLSv1
except:
    HAVE_SSL = False
    cert_reqs = None
    tls_version = None
import struct
import sys
import threading
import time
HAVE_DNS = True
try:
    import dns.resolver
except ImportError:
    HAVE_DNS = False

if platform.system() == 'Windows':
    EAGAIN = errno.WSAEWOULDBLOCK
else:
    EAGAIN = errno.EAGAIN

VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_REVISION = 0
VERSION_NUMBER = (VERSION_MAJOR * 1000000 + VERSION_MINOR * 1000 + VERSION_REVISION)


# Connection state
class MQTTConnectionState(Enum):
    NEW = 0
    CONNECTED = 1
    DISCONNECTING = 2
    CONNECT_ASYNC = 3


if sys.version_info[0] < 3:
    sockpair_data = "0"
else:
    sockpair_data = b"0"


def _socketpair_compat():
    """TCP/IP socketpair including Windows support"""
    listensock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_IP)
    listensock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listensock.bind(("127.0.0.1", 0))
    listensock.listen(1)

    iface, port = listensock.getsockname()
    sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_IP)
    sock1.setblocking(0)
    try:
        sock1.connect(("localhost", port))
    except socket.error as err:
        if err.errno != errno.EINPROGRESS and err.errno != errno.EWOULDBLOCK and err.errno != EAGAIN:
            raise
    sock2, address = listensock.accept()
    sock2.setblocking(0)
    listensock.close()
    return (sock1, sock2)


class MockBroker(object):
    """MQTT version 3.1/3.1.1 mock server class. It means that this broker is easily configurable
    to get it into a desired state. This server is meant for testing MQTT clients.

    This is the main class for use communicating with an MQTT client.

    General usage flow:

    * Call loop() frequently to maintain network traffic flow with the broker
    * Or use loop_start() to set a thread running to call loop() for you.
    * Or use loop_forever() to handle calling loop() for you in a blocking
    * function.
    * Use disconnect() to disconnect the connected client

    Data returned from the client is made available with the use of callback
    functions as described below.

    Callbacks
    =========

    A number of callback functions are available to receive data back from the
    client. To use a callback, define a function and then assign it to the
    broker:

    def on_client_connect(broker, userdata, connect_options):
        print("Client connected with " + str(connect_options))

    broker.on_client_connect = on_client_connect

    All of the callbacks as described below have a "broker" and an "userdata"
    argument. "broker" is the mock broker instance that is calling the callback.
    "userdata" is user data of any type and can be set when creating a new broker
    instance or with user_data_set(userdata). It is "Mock Broker" by default.

    The callbacks:

    on_client_connect(broker, userdata, connect_options): called when the client sends the connect message to
      the broker. The connect_options variable contains MQTT connection data such as protocol name and version,
      username, password, client ID, will topic and message if provided.

    on_client_disconnect(broker, userdata, rc): called when the client disconnects from the broker.
      The rc parameter indicates the disconnection state. If MQTT_ERR_SUCCESS
      (0), the callback was called in response to a disconnect() call. In case of any
      other value, the disconnection was unexpected, such as might be caused by
      a network error.

    on_message(broker, userdata, message): called when the broker receives a message. The message variable
      is an MQTTMessage that describes all of the message parameters.

    on_connack(broker): called when broker connack message is sent

    on_publish(broker, userdata, msg_id): called when a message that was to be sent using the
      publish() call has completed transmission to the client. For messages
      with QoS levels 1 and 2, this means that the appropriate handshakes have
      completed. For QoS 0, this simply means that the message has left the
      broker. The msg_id variable matches the msg_id variable returned from the
      corresponding publish() call, to allow outgoing messages to be tracked.
      This callback is important because even if the publish() call returns
      success, it does not always mean that the message has been sent.

    on_client_subscribe(broker, userdata, msg_id, topics_and_qos): called when the client subscribes to
      the topics passed in the topics_and_qos variable. That variable is a list where each
      item is a pair of topic name and the required qos. The response message to the SUBSCRIBE
      message must contain the same msg_id.

    on_client_unsubscribe(broker, userdata, msg_id, topics): called when the client unsubscribes from
      the topics passed in the topics variable. The response message to the UNSUBSCRIBE message
      must contain the same msg_id.

    on_log(broker, userdata, log_level, message): called when the broker has log information.
      Define to allow debugging. The level variable gives the severity of the message
      and will be one of MQTT_LOG_INFO, MQTT_LOG_NOTICE, MQTT_LOG_WARNING,
      MQTT_LOG_ERR, and MQTT_LOG_DEBUG.

    """

    MAX_CONNECT_TIMEOUT = 4.0

    def __init__(self,use_websocket):
        self._server_socket = None
        self._sock = None
        self._sockpairR, self._sockpairW = (None, None)
        self._keep_alive = 0
        self._userdata = "[ MockBroker ]"

        self._decoded_packet = {
            "command": 0,
            "have_remaining": 0,
            "remaining_count": [],
            "remaining_mult": 1,
            "remaining_length": 0,
            "packet": b"",
            "to_process": 0,
            "pos": 0}
        self._out_packet = []
        self._current_out_packet = None
        self._last_msg_in = time.time()
        self._last_msg_out = time.time()
        self._last_mid = 0
        self._state = MQTTConnectionState.NEW
        self._out_messages = []
        self._in_messages = []
        self._max_inflight_messages = 20
        self._inflight_messages = 0

        self.on_client_connect = None
        self.on_client_disconnect = None
        self.on_publish = None
        self.on_connack = None
        self.on_message = None
        self.on_client_subscribe = None
        self.on_client_unsubscribe = None
        self.on_log = None

        self._host = "localhost"
        self._port = 0
        self.bind_address = ""
        self._in_callback = False
        self._strict_protocol = False
        self._callback_mutex = threading.RLock()
        self._state_mutex = threading.Lock()
        self._out_packet_mutex = threading.Lock()
        self._current_out_packet_mutex = threading.Lock()
        self._msgtime_mutex = threading.Lock()
        self._out_message_mutex = threading.Lock()
        self._in_message_mutex = threading.Lock()
        self._thread = None
        self._thread_terminate = False
        self._mqtt_codec = None

        self._ssl = None
        self._tls_certfile = None
        self._tls_keyfile = None
        self._tls_ca_certs = None
        self._tls_cert_reqs = None
        self._tls_ciphers = None
        self._tls_version = tls_version
        self._tls_insecure = False

        self._use_websocket = use_websocket
        self._websocket_certfile = None
        self._websocket_keyfile = None
        self._websocket_proxy = None
        self._shutdown_after_last_packet_sent = False

    def __del__(self):
        self._network_shutdown()

    def reinitialise(self):
        self._network_shutdown()
        self.__init__()

    def setup_tls(self, certfile, keyfile=None, ca_certs=None, cert_reqs=cert_reqs, tls_version=tls_version, ciphers=None):
        """Configure network encryption and authentication options. Enables SSL/TLS support.

        ca_certs : a string path to the Certificate Authority certificate files
        that are to be treated as trusted by this client. If this is the only
        option given then the client will operate in a similar manner to a web
        browser. That is to say it will require the broker to have a
        certificate signed by the Certificate Authorities in ca_certs and will
        communicate using TLS v1, but will not attempt any form of
        authentication. This provides basic network encryption but may not be
        sufficient depending on how the broker is configured.

        certfile and keyfile are strings pointing to the PEM encoded client
        certificate and private keys respectively. If these arguments are not
        None then they will be used as client information for TLS based
        authentication.  Support for this feature is broker dependent. Note
        that if either of these files in encrypted and needs a password to
        decrypt it, Python will ask for the password at the command line. It is
        not currently possible to define a callback to provide the password.

        cert_reqs allows the certificate requirements that the client imposes
        on the broker to be changed. By default this is ssl.CERT_OPTIONAL,
        which means that the client is not asked for certificate, but
        if the client provides it, the broker validates it.

        tls_version allows the version of the SSL/TLS protocol used to be
        specified. By default TLS v1 is used. Previous versions (all versions
        beginning with SSL) are possible but not recommended due to possible
        security problems.

        ciphers is a string specifying which encryption ciphers are allowable
        for this connection, or None to use the defaults. See the ssl pydoc for
        more information.

        """

        if self._use_websocket == False:

            if HAVE_SSL is False:
                raise ValueError('This platform has no SSL/TLS.')

            if sys.version < '2.7':
                raise ValueError('Python 2.7 is the minimum supported version for TLS.')

            if certfile is None:
                raise ValueError('SSL cert file must not be None.')

            if ca_certs is not None:
                try:
                    f = open(ca_certs, "r")
                except IOError as err:
                    raise IOError(ca_certs+": "+err.strerror)
                else:
                    f.close()

            # Check the certificate file
            try:
                f = open(certfile, "r")
            except IOError as err:
                raise IOError(certfile+": "+err.strerror)
            else:
                f.close()

            if keyfile is not None:
                try:
                    f = open(keyfile, "r")
                except IOError as err:
                    raise IOError(keyfile+": "+err.strerror)
                else:
                    f.close()

            self._tls_ca_certs = ca_certs
            self._tls_certfile = certfile
            self._tls_keyfile = keyfile
            self._tls_cert_reqs = cert_reqs
            self._tls_version = tls_version
            self._tls_ciphers = ciphers

        else :

            self._websocket_certfile = certfile
            self._websocket_keyfile = keyfile

    def tls_insecure_set(self, value):
        """Configure verification of the client.

        Do not use this function in a real system. Setting value to true means
        there is no point using encryption.

        Must be called before connect()."""
        if HAVE_SSL is False:
            raise ValueError('This platform has no SSL/TLS.')

        self._tls_insecure = value

    def loop(self, timeout=1.0, max_packets=1):
        """Process network events.

        This function must be called regularly to ensure communication with the
        client is carried out. It calls select() on the network socket to wait
        for network events. If incoming data is present it will then be
        processed. Outgoing commands, from e.g. publish(), are normally sent
        immediately that their function is called, but this is not always
        possible. loop() will also attempt to send any remaining outgoing
        messages, which also includes commands that are part of the flow for
        messages with QoS>0.

        timeout: The time in seconds to wait for incoming/outgoing network
          traffic before timing out and returning.
        max_packets: Not currently used.

        Returns MQTT_ERR_SUCCESS on success.
        Returns >0 on error.

        A ValueError will be raised if timeout < 0"""
        if timeout < 0.0:
            raise ValueError('Invalid timeout.')

        self._current_out_packet_mutex.acquire()
        self._out_packet_mutex.acquire()
        if self._current_out_packet is None and len(self._out_packet) > 0:
            self._current_out_packet = self._out_packet.pop(0)

        if self._current_out_packet:
            wlist = [self.socket()]
        else:
            wlist = []
        self._out_packet_mutex.release()
        self._current_out_packet_mutex.release()

        # sockpairR is used to break out of select() before the timeout, on a
        # call to publish() etc.
        rlist = [self.socket(), self._sockpairR]
        try:
            socklist = select.select(rlist, wlist, [], timeout)
        except TypeError:
            # Socket isn't correct type, in likelihood connection is lost
            return MQTT_ERR_CONN_LOST
        except ValueError:
            # Can occur if we just reconnected but rlist/wlist contain a -1 for
            # some reason.
            return MQTT_ERR_CONN_LOST
        except:
            return MQTT_ERR_UNKNOWN

        if self.socket() in socklist[0]:
            rc = self.loop_read(max_packets)
            if rc or (self._ssl is None and self._sock is None):
                return rc

        if self._sockpairR in socklist[0]:
            # Stimulate output write even though we didn't ask for it, because
            # at that point the publish or other command wasn't present.
            socklist[1].insert(0, self.socket())
            # Clear sockpairR - only ever a single byte written.
            try:
                self._sockpairR.recv(1)
            except socket.error as err:
                if err.errno != EAGAIN:
                    raise

        if self.socket() in socklist[1]:
            rc = self.loop_write(max_packets)
            if rc or (self._ssl is None and self._sock is None):
                return rc

        return self.loop_misc()

    def publish(self, topic, payload=None, qos=0, retain=False):
        """Publish a message on a topic.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        topic: The topic that the message should be published on.
        payload: The actual message to send. If not given, or set to None a
        zero length message will be used. Passing an int or float will result
        in the payload being converted to a string representing that number. If
        you wish to send a true int/float, use struct.pack() to create the
        payload you require.
        qos: The quality of service level to use.
        retain: If set to true, the message will be set as the "last known
        good"/retained message for the topic.

        Returns a tuple (result, mid), where result is MQTT_ERR_SUCCESS to
        indicate success or MQTT_ERR_NO_CONN if the client is not currently
        connected.  mid is the message ID for the publish request. The mid
        value can be used to track the publish request by checking against the
        mid argument in the on_publish() callback if it is defined.

        A ValueError will be raised if topic is None, has zero length or is
        invalid (contains a wildcard), if qos is not one of 0, 1 or 2, or if
        the length of the payload is greater than 268435455 bytes."""
        if topic is None or len(topic) == 0:
            raise ValueError('Invalid topic.')
        if qos<0 or qos>2:
            raise ValueError('Invalid QoS level.')
        if isinstance(payload, str) or isinstance(payload, bytearray):
            local_payload = payload
        elif sys.version_info[0] < 3 and isinstance(payload, unicode):
            local_payload = payload
        elif isinstance(payload, int) or isinstance(payload, float):
            local_payload = str(payload)
        elif payload is None:
            local_payload = None
        else:
            raise TypeError('payload must be a string, bytearray, int, float or None.')

        if local_payload is not None and len(local_payload) > 268435455:
            raise ValueError('Payload too large.')

        if self._topic_wildcard_len_check(topic) != MQTT_ERR_SUCCESS:
            raise ValueError('Publish topic cannot contain wildcards.')

        local_mid = self._generate_msg_id()

        if qos == 0:
            rc = self._send_publish(local_mid, topic, local_payload, qos, retain, False)
            return (rc, local_mid)
        else:
            message = MQTTMessage()
            message.timestamp = time.time()

            message.mid = local_mid
            message.topic = topic
            if local_payload is None or len(local_payload) == 0:
                message.payload = None
            else:
                message.payload = local_payload

            message.qos = qos
            message.retain = retain
            message.dup = False

            self._out_message_mutex.acquire()
            self._out_messages.append(message)
            if self._max_inflight_messages == 0 or self._inflight_messages < self._max_inflight_messages:
                self._inflight_messages += 1
                if qos == 1:
                    message.state = mqtt_ms_wait_for_puback
                elif qos == 2:
                    message.state = mqtt_ms_wait_for_pubrec
                self._out_message_mutex.release()

                rc = self._send_publish(message.mid, message.topic, message.payload, message.qos, message.retain, message.dup)

                # remove from inflight messages so it will be send after a connection is made
                if rc is MQTT_ERR_NO_CONN:
                    with self._out_message_mutex:
                        self._inflight_messages -= 1
                        message.state = mqtt_ms_publish

                return (rc, local_mid)
            else:
                message.state = mqtt_ms_queued
                self._out_message_mutex.release()
                return (MQTT_ERR_SUCCESS, local_mid)

    def disconnect(self):
        """Disconnect the connected client from the broker."""
        self._easy_log(MQTT_LOG_DEBUG, "DISCONNECT the client")

        self.empty_out_queues()

        if self._sock is None and self._ssl is None:
            return MQTT_ERR_NO_CONN

        self._close_client_socket()

        self._callback_mutex.acquire()
        if self.on_client_disconnect:
            self._in_callback = True
            self.on_client_disconnect(self, self._userdata, MQTT_ERR_SUCCESS)
            self._in_callback = False
        self._callback_mutex.release()

        return MQTT_ERR_SUCCESS

    def loop_read(self, max_packets=1):
        """Process read network events. Use in place of calling loop() if you
        wish to handle your client reads as part of your own application.

        Use socket() to obtain the client socket to call select() or equivalent
        on.

        Do not use if you are using the threaded interface loop_start()."""
        if self._sock is None and self._ssl is None:
            return MQTT_ERR_NO_CONN

        max_packets = len(self._out_messages) + len(self._in_messages)
        if max_packets < 1:
            max_packets = 1

        for i in range(0, max_packets):
            rc = self._packet_read()
            if rc > 0:
                return self._loop_rc_handle(rc)
            elif rc == MQTT_ERR_AGAIN:
                return MQTT_ERR_SUCCESS
        return MQTT_ERR_SUCCESS

    def loop_write(self, max_packets=1):
        """Process read network events. Use in place of calling loop() if you
        wish to handle your client reads as part of your own application.

        Use socket() to obtain the client socket to call select() or equivalent
        on.

        Use want_write() to determine if there is data waiting to be written.

        Do not use if you are using the threaded interface loop_start()."""
        if self._sock is None and self._ssl is None:
            return MQTT_ERR_NO_CONN

        max_packets = len(self._out_packet) + 1
        if max_packets < 1:
            max_packets = 1

        for i in range(0, max_packets):
            rc = self._packet_write()
            if rc > 0:
                return self._loop_rc_handle(rc)
            elif rc == MQTT_ERR_AGAIN:
                return MQTT_ERR_SUCCESS
        return MQTT_ERR_SUCCESS

    def want_write(self):
        """Call to determine if there is network data waiting to be written.
        Useful if you are calling select() yourself rather than using loop().
        """
        if self._current_out_packet or len(self._out_packet) > 0:
            return True
        else:
            return False

    def loop_misc(self):
        """Process miscellaneous network events. Use in place of calling loop() if you
        wish to call select() or equivalent on.

        Do not use if you are using the threaded interface loop_start()."""
        if self._sock is None and self._ssl is None:
            return MQTT_ERR_NO_CONN
        return MQTT_ERR_SUCCESS

    def max_inflight_messages_set(self, inflight):
        """Set the maximum number of messages with QoS>0 that can be part way
        through their network flow at once. Defaults to 20."""
        if inflight < 0:
            raise ValueError('Invalid inflight.')
        self._max_inflight_messages = inflight

    def socket(self):
        """Return the socket or ssl object for this client."""
        if self._ssl:
            return self._ssl
        else:
            return self._sock

    def loop_forever(self, timeout=1.0, max_packets=1, retry_first_connection=False):
        """This function call loop() for you in an infinite blocking loop. It
        is useful for the case where you only want to run the MQTT client loop
        in your program.

        loop_forever() will handle reconnecting for you. If you call
        disconnect() in a callback it will return.


        timeout: The time in seconds to wait for incoming/outgoing network
          traffic before timing out and returning.
        max_packets: Not currently used.
        retry_first_connection: Should the first connection attempt be retried on failure.

        Raises socket.error on first connection failures unless retry_first_connection=True
        """

        rc = 0  # return code

        self._sockpairR, self._sockpairW = _socketpair_compat()

        while True:

            if self._thread_terminate is True:
                break

            # Wait for a connection
            self._easy_log(MQTT_LOG_INFO, "waiting for a connection")

            try:
                self._sock, client_address = self._server_socket.accept()
                if self._tls_certfile is not None:
                    try:
                        self._ssl = ssl.wrap_socket(
                            self._sock,
                            certfile=self._tls_certfile,
                            server_side=True,
                            keyfile=self._tls_keyfile,
                            ca_certs=self._tls_ca_certs,
                            cert_reqs=self._tls_cert_reqs,
                            ssl_version=self._tls_version,
                            suppress_ragged_eofs=False,
                            ciphers=self._tls_ciphers)
                    except (ssl.SSLError, ssl.CertificateError) as ssl_err:
                        self._easy_log(MQTT_LOG_ERR, "Failed to wrap socket into SSL: " + str(ssl_err))
                        continue

                self._mqtt_codec = MQTTCodec(self._sock, self._ssl)
                self._mqtt_codec.on_packet_decoded = self._packet_handle
                self._mqtt_codec.on_packet_encoded = self._packet_queue

                self._easy_log(MQTT_LOG_INFO, "connection from " + str(client_address))

                # Receive the data in small chunks and retransmit it
                while True:
                    rc = self.loop(3.0, max_packets)
                    # We don't need to worry about locking here, because we've
                    # either called loop_forever() when in single threaded mode, or
                    # in multi threaded mode when loop_stop() has been called and
                    # so no other threads can access _current_out_packet,
                    # _out_packet or _messages.
                    if (self._thread_terminate is True
                        and self._current_out_packet is None
                        and len(self._out_packet) == 0
                        and len(self._out_messages) == 0):

                        return

                    if rc != 0:
                        self._easy_log(MQTT_LOG_ERR, "self.loop return code is not success - rc = " + str( rc ) )
                        break

            except socket.error as msg:
                pass
            except Exception as err:
                #self._easy_log(MQTT_LOG_ERR, "Exception caught in loop_forever: " + traceback.format_exc(err))
                self._easy_log(MQTT_LOG_ERR, "Exception caught in loop_forever: " + str(err))
                return
            finally:
                # Clean up the client connection
                self._close_client_socket()

        self._network_shutdown()
        return rc

    def loop_start(self):
        """This is part of the threaded client interface. Call this once to
        start a new thread to process network traffic. This provides an
        alternative to repeatedly calling loop() yourself.
        """
        if self._thread is not None:
            return MQTT_ERR_INVAL

        start_stamp = time.time()
        while True:
            try:
                # Find an available port
                listensock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_IP)
                listensock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listensock.bind(("localhost", 0))
                listensock.listen(1)

                iface, port = listensock.getsockname()
                self._port = port
                listensock.close()

                # Bind the socket to the port
                server_address = (self._host, port)
                self.bind_address = server_address

                self._easy_log(MQTT_LOG_INFO, "starting up MockBroker on %s port %s" % self.bind_address )

                # Create a TCP/IP socket that the server listens on
                self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._server_socket.bind(server_address)
                break

            except OSError as err:
                if "Address already in use" in err.strerror:
                    continue

                if time.time() - start_stamp > self.MAX_CONNECT_TIMEOUT:
                    self._easy_log(MQTT_LOG_ERR, "no free ports available for the mock broker" )
                    raise

        # Listen for incoming connections
        self._server_socket.listen(1)

        # start ws proxy if needed
        if self._use_websocket:

            try:

                self._websocket_proxy = XiWebSocketProxyServer( )
                self._websocket_proxy.start( "localhost" , self.bind_address[1] , self._websocket_certfile, self._websocket_keyfile )
                self.bind_address = self._websocket_proxy.address

                self._easy_log(MQTT_LOG_INFO, "websocket proxy starting up on %s port %s" % self.bind_address )

            except Exception as inst:

                print( "MockBroker proxy server exception :" , inst )


        self._thread_terminate = False
        self._thread = threading.Thread(target=self._thread_main)
        self._thread.daemon = True
        self._thread.start()

    def loop_stop(self, force=False):
        """This is part of the threaded client interface. Call this once to
        stop the network thread previously created with loop_start(). This call
        will block until the network thread finishes.

        The force parameter is currently ignored.
        """
        if self._thread is None:
            return MQTT_ERR_INVAL

        self.trigger_shutdown()

        self.execute()

    def trigger_shutdown(self,shutdown_after_last_packet_sent=False):
        self._shutdown_after_last_packet_sent = shutdown_after_last_packet_sent
        if not shutdown_after_last_packet_sent:
            self._thread_terminate = True
            self._close_server_socket()
            self._close_client_socket()
            if self._websocket_proxy != None:

                self._websocket_proxy.stop()
                self._websocket_proxy = None

    def execute(self, timeout=None):
        """ This function only returns when the broker is shutting down.
        :return: none
        """
        self._thread.join(timeout)

        if self._thread.isAlive():

            self._thread = None
            # Thread is still alive, which means join has timed out.
            return False

        self._thread = None
        return True

    # ============================================================
    # Private functions
    # ============================================================

    def _loop_rc_handle(self, rc):
        if rc:
            self._close_client_socket()

            self._state_mutex.acquire()
            if self._state == MQTTConnectionState.DISCONNECTING:
                rc = MQTT_ERR_SUCCESS
            self._state_mutex.release()
            self._callback_mutex.acquire()
            if self.on_client_disconnect:
                self._in_callback = True
                self.on_client_disconnect(self, self._userdata, rc)
                self._in_callback = False

            self.empty_out_queues()
            self._callback_mutex.release()
        return rc

    def _packet_read(self):
        # This gets called if pselect() indicates that there is network data
        # available - ie. at least one byte.  What we do depends on what data we
        # already have.
        # If we've not got a command, attempt to read one and save it. This should
        # always work because it's only a single byte.
        # Then try to read the remaining length. This may fail because it is may
        # be more than one byte - will need to save data pending next read if it
        # does fail.
        # Then try to read the remaining payload, where 'payload' here means the
        # combined variable header and actual payload. This is the most likely to
        # fail due to longer length, so save current data and current position.
        # After all data is read, send to _mqtt_handle_packet() to deal with.
        # Finally, free the memory and reset everything to starting conditions.

        rc = self._mqtt_codec.decode_packet()

        self._msgtime_mutex.acquire()
        self._last_msg_in = time.time()
        self._msgtime_mutex.release()
        return rc

    def _packet_write(self):
        self._current_out_packet_mutex.acquire()

        while self._current_out_packet:
            packet = self._current_out_packet

            try:
                if self._ssl:
                    write_length = self._ssl.write(packet['packet'][packet['pos']:])
                else:
                    write_length = self._sock.send(packet['packet'][packet['pos']:])
            except AttributeError:
                self._current_out_packet_mutex.release()
                return MQTT_ERR_SUCCESS
            except socket.error as err:
                self._current_out_packet_mutex.release()
                if self._ssl and (err.errno == ssl.SSL_ERROR_WANT_READ or err.errno == ssl.SSL_ERROR_WANT_WRITE):
                    return MQTT_ERR_AGAIN
                if err.errno == EAGAIN:
                    return MQTT_ERR_AGAIN
                self._easy_log(MQTT_LOG_ERR, "Failed to write packet! Error: " + str(err))
                return 1

            if write_length > 0:
                packet['to_process'] = packet['to_process'] - write_length
                packet['pos'] = packet['pos'] + write_length

                if packet['to_process'] == 0:
                    if (packet['command'] & 0xF0) == PUBLISH and packet['qos'] == 0:
                        self._callback_mutex.acquire()
                        if self.on_publish:
                            self._in_callback = True
                            self.on_publish(self, self._userdata, packet['mid'])
                            self._in_callback = False
                    #if (packet['command'] & 0xF0) == CONNACK:
                    #    self._callback_mutex.acquire()
                    #    if self.on_connack:
                    #        self._in_callback = True
                    #        self.on_connack(self)
                    #        self._in_callback = False

                        self._callback_mutex.release()

                    self._out_packet_mutex.acquire()
                    if len(self._out_packet) > 0:
                        self._current_out_packet = self._out_packet.pop(0)
                    else:
                        self._current_out_packet = None
                        if self._shutdown_after_last_packet_sent is True:
                            self.trigger_shutdown(False)
                    self._out_packet_mutex.release()
            else:
                pass  # FIXME

        self._current_out_packet_mutex.release()

        self._msgtime_mutex.acquire()
        self._last_msg_out = time.time()
        self._msgtime_mutex.release()

        return MQTT_ERR_SUCCESS

    def _easy_log(self, log_level, message):
        if self.on_log:
            self.on_log(self, self._userdata, log_level, message)

    def _generate_msg_id(self):
        self._last_mid += 1
        if self._last_mid == 65536:
            self._last_mid = 1
        return self._last_mid

    def send_pingresp(self):
        self._easy_log(MQTT_LOG_DEBUG, "Sending PINGRESP")
        return self._mqtt_codec.encode_pingresp()

    def send_puback(self, mid):
        self._easy_log(MQTT_LOG_DEBUG, "Sending PUBACK (Mid: "+str(mid)+")")
        return self._mqtt_codec.encode_puback(mid)

    def _send_pubcomp(self, mid):
        self._easy_log(MQTT_LOG_DEBUG, "Sending PUBCOMP (Mid: "+str(mid)+")")
        return self._mqtt_codec.encode_pubcomp(mid)

    def _send_publish(self, mid, topic, payload=None, qos=0, retain=False, dup=False):
        if self._sock is None and self._ssl is None:
            return MQTT_ERR_NO_CONN

        return self._mqtt_codec.encode_publish(mid, topic, payload, qos, retain, dup)

    def _send_pubrec(self, mid):
        self._easy_log(MQTT_LOG_DEBUG, "Sending PUBREC (Mid: "+str(mid)+")")
        return self._mqtt_codec.encode_pubrec(mid)

    def _send_pubrel(self, mid, dup=False):
        self._easy_log(MQTT_LOG_DEBUG, "Sending PUBREL (Mid: "+str(mid)+")")
        return self._mqtt_codec.encode_pubrel(mid, dup)

    def send_connack(self, connack_result_code):
        return self._mqtt_codec.encode_connack(connack_result_code)

    def send_suback(self, mid, topics_and_qos):
        self._mqtt_codec.encode_suback(mid, topics_and_qos)
        return MQTT_ERR_SUCCESS

    def send_unsuback(self, mid, topics):
        self._mqtt_codec.encode_unsuback(mid, topics)
        return MQTT_ERR_SUCCESS

    def _messages_reconnect_reset_out(self):
        self._out_message_mutex.acquire()
        self._inflight_messages = 0
        for m in self._out_messages:
            m.timestamp = 0
            if self._max_inflight_messages == 0 or self._inflight_messages < self._max_inflight_messages:
                if m.qos == 0:
                    m.state = mqtt_ms_publish
                elif m.qos == 1:
                    #self._inflight_messages = self._inflight_messages + 1
                    if m.state == mqtt_ms_wait_for_puback:
                        m.dup = True
                    m.state = mqtt_ms_publish
                elif m.qos == 2:
                    #self._inflight_messages = self._inflight_messages + 1
                    if m.state == mqtt_ms_wait_for_pubcomp:
                        m.state = mqtt_ms_resend_pubrel
                        m.dup = True
                    else:
                        if m.state == mqtt_ms_wait_for_pubrec:
                            m.dup = True
                        m.state = mqtt_ms_publish
            else:
                m.state = mqtt_ms_queued
        self._out_message_mutex.release()

    def _messages_reconnect_reset_in(self):
        self._in_message_mutex.acquire()
        for m in self._in_messages:
            m.timestamp = 0
            if m.qos != 2:
                self._in_messages.pop(self._in_messages.index(m))
            else:
                # Preserve current state
                pass
        self._in_message_mutex.release()

    def _messages_reconnect_reset(self):
        self._messages_reconnect_reset_out()
        self._messages_reconnect_reset_in()

    def _packet_queue(self, command, packet, mid, qos):
        mpkt = dict(
            command = command,
            mid = mid,
            qos = qos,
            pos = 0,
            to_process = len(packet),
            packet = packet)

        self._out_packet_mutex.acquire()
        self._out_packet.append(mpkt)
        if self._current_out_packet_mutex.acquire(False):
            if self._current_out_packet is None and len(self._out_packet) > 0:
                self._current_out_packet = self._out_packet.pop(0)
            self._current_out_packet_mutex.release()
        self._out_packet_mutex.release()

        # Write a single byte to sockpairW (connected to sockpairR) to break
        # out of select() if in threaded mode.
        try:
            self._sockpairW.send(sockpair_data)
        except socket.error as err:
            if err.errno != EAGAIN:
                raise

        if not self._in_callback and self._thread is None:
            return self.loop_write()
        else:
            return MQTT_ERR_SUCCESS

    def show_queue(self):
        self._out_packet_mutex.acquire()
        self._easy_log(MQTT_LOG_DEBUG, str(self._current_out_packet))
        self._out_packet_mutex.release()

    def empty_out_queues(self):
        self._current_out_packet_mutex.acquire()
        self._current_out_packet = None
        self._current_out_packet_mutex.release()

        self._out_packet_mutex.acquire()
        self._out_packet = []
        self._out_packet_mutex.release()


    def _packet_handle(self, decoded_packet):
        self._decoded_packet = decoded_packet
        cmd = self._decoded_packet['command']&0xF0
        if cmd == PINGREQ:
            return self._handle_pingreq()
        elif cmd == PUBACK:
            return self._handle_pubackcomp("PUBACK")
        elif cmd == PUBCOMP:
            return self._handle_pubackcomp("PUBCOMP")
        elif cmd == PUBLISH:
            return self._handle_publish()
        elif cmd == PUBREC:
            return self._handle_pubrec()
        elif cmd == PUBREL:
            return self._handle_pubrel()
        elif cmd == CONNECT:
            return self._handle_connect()
        elif cmd == SUBSCRIBE:
            return self._handle_subscribe()
        elif cmd == UNSUBSCRIBE:
            return self._handle_unsubscribe()
        elif cmd == DISCONNECT:
            return self.disconnect()
        elif cmd == CONNACK  or cmd == SUBACK or \
             cmd == UNSUBACK or cmd == PINGRESP:
            self._easy_log(MQTT_LOG_ERR, "Error: Broker received unexpected command " + str(cmd))
            return MQTT_ERR_PROTOCOL
        else:
            # If we don't recognise the command, return an error straight away.
            self._easy_log(MQTT_LOG_ERR, "Error: Unrecognised command " + str(cmd))
            return MQTT_ERR_PROTOCOL

    def _handle_pingreq(self):
        if self._strict_protocol:
            if self._decoded_packet['remaining_length'] != 0:
                return MQTT_ERR_PROTOCOL

        self._easy_log(MQTT_LOG_DEBUG, "Received PINGREQ")
        return self.send_pingresp()

    def _handle_connect(self):
        self._easy_log(MQTT_LOG_DEBUG, "Received CONNECT")

        connect_options = MQTTConnectOptions.from_mqtt_packet(self._decoded_packet['packet'])

        self._keep_alive = connect_options.keep_alive

        self._callback_mutex.acquire()
        if self.on_client_connect:
            self._in_callback = True
            self.on_client_connect(self._userdata, connect_options)
            self._in_callback = False
        else:
            self.send_connack(CONNACK_ACCEPTED)
        self._callback_mutex.release()
        return MQTT_ERR_SUCCESS

    def _handle_subscribe(self):
        self._easy_log(MQTT_LOG_DEBUG, "Received SUBSCRIBE")

        header = self._decoded_packet['command']
        dup = (header & 0x08)>>3

        msg_id, topics_and_qos = MQTTCodec.decode_subscribe_packet(self._decoded_packet['packet'],
                                                                   self._decoded_packet['remaining_length'])
        self._callback_mutex.acquire()
        if self.on_client_subscribe:
            self._in_callback = True
            self.on_client_subscribe(self._userdata, msg_id, topics_and_qos, dup)
            self._in_callback = False
        else:
            self.send_suback(msg_id, topics_and_qos)
        self._callback_mutex.release()
        return MQTT_ERR_SUCCESS

    def _handle_unsubscribe(self):
        self._easy_log(MQTT_LOG_DEBUG, "Received SUBSCRIBE")
        msg_id, topics = MQTTCodec.decode_unsubscribe_packet(self._decoded_packet['packet'],
                                                             self._decoded_packet['remaining_length'])
        self._callback_mutex.acquire()
        if self.on_client_unsubscribe:
            self._in_callback = True
            self.on_client_unsubscribe(self._userdata, msg_id, topics)
            self._in_callback = False
        else:
            self.send_unsuback(msg_id, topics)
        self._callback_mutex.release()
        return MQTT_ERR_SUCCESS

    def _handle_publish(self):
        #self._easy_log(MQTT_LOG_DEBUG, "Received PUBLISH")

        header = self._decoded_packet['command']
        message = MQTTMessage()
        message.dup = (header & 0x08)>>3
        message.qos = (header & 0x06)>>1
        message.retain = (header & 0x01)

        pack_format = "!H" + str(len(self._decoded_packet['packet'])-2) + 's'
        (slen, packet) = struct.unpack(pack_format, self._decoded_packet['packet'])
        pack_format = '!' + str(slen) + 's' + str(len(packet)-slen) + 's'
        (message.topic, packet) = struct.unpack(pack_format, packet)

        if len(message.topic) == 0:
            return MQTT_ERR_PROTOCOL

        if sys.version_info[0] >= 3:
            message.topic = message.topic.decode('utf-8')

        if message.qos > 0:
            pack_format = "!H" + str(len(packet)-2) + 's'
            (message.mid, packet) = struct.unpack(pack_format, packet)

        message.payload = packet

        self._easy_log(
            MQTT_LOG_DEBUG,
            "Received PUBLISH (d"+str(message.dup)+
            ", q"+str(message.qos)+", r"+str(message.retain)+
            ", m"+str(message.mid)+", '"+message.topic+
            ", [ "+str(message.payload)+
            " ] - "+str(len(message.payload))+" bytes")

        message.timestamp = time.time()
        if message.qos == 0:
            self._handle_on_message(message)
            return MQTT_ERR_SUCCESS
        elif message.qos == 1:
            #rc = self.send_puback(message.mid)
            rc = MQTT_ERR_SUCCESS
            self._handle_on_message(message)
            return rc
        elif message.qos == 2:
            #rc = self._send_pubrec(message.mid)
            rc = MQTT_ERR_SUCCESS
            message.state = mqtt_ms_wait_for_pubrel
            self._in_message_mutex.acquire()
            self._in_messages.append(message)
            self._in_message_mutex.release()
            return rc
        else:
            return MQTT_ERR_PROTOCOL

    def _handle_pubrel(self):
        if self._strict_protocol:
            if self._decoded_packet['remaining_length'] != 2:
                return MQTT_ERR_PROTOCOL

        if len(self._decoded_packet['packet']) != 2:
            return MQTT_ERR_PROTOCOL

        mid = struct.unpack("!H", self._decoded_packet['packet'])
        mid = mid[0]
        self._easy_log(MQTT_LOG_DEBUG, "Received PUBREL (Mid: "+str(mid)+")")

        self._in_message_mutex.acquire()
        for i in range(len(self._in_messages)):
            if self._in_messages[i].mid == mid:

                # Only pass the message on if we have removed it from the queue - this
                # prevents multiple callbacks for the same message.
                self._handle_on_message(self._in_messages[i])
                self._in_messages.pop(i)
                self._inflight_messages -= 1
                if self._max_inflight_messages > 0:
                    self._out_message_mutex.acquire()
                    rc = self._update_inflight()
                    self._out_message_mutex.release()
                    if rc != MQTT_ERR_SUCCESS:
                        self._in_message_mutex.release()
                        return rc

                self._in_message_mutex.release()
                return self._send_pubcomp(mid)

        self._in_message_mutex.release()
        return MQTT_ERR_SUCCESS

    def _update_inflight(self):
        # Don't lock message_mutex here
        for m in self._out_messages:
            if self._inflight_messages < self._max_inflight_messages:
                if m.qos > 0 and m.state == mqtt_ms_queued:
                    self._inflight_messages += 1
                    if m.qos == 1:
                        m.state = mqtt_ms_wait_for_puback
                    elif m.qos == 2:
                        m.state = mqtt_ms_wait_for_pubrec
                    rc = self._send_publish(m.mid, m.topic, m.payload, m.qos, m.retain, m.dup)
                    if rc != 0:
                        return rc
            else:
                return MQTT_ERR_SUCCESS
        return MQTT_ERR_SUCCESS

    def _handle_pubrec(self):
        if self._strict_protocol:
            if self._decoded_packet['remaining_length'] != 2:
                return MQTT_ERR_PROTOCOL

        mid = struct.unpack("!H", self._decoded_packet['packet'])
        mid = mid[0]
        self._easy_log(MQTT_LOG_DEBUG, "Received PUBREC (Mid: "+str(mid)+")")

        self._out_message_mutex.acquire()
        for m in self._out_messages:
            if m.mid == mid:
                m.state = mqtt_ms_wait_for_pubcomp
                m.timestamp = time.time()
                self._out_message_mutex.release()
                return self._send_pubrel(mid, False)

        self._out_message_mutex.release()
        return MQTT_ERR_SUCCESS

    def _handle_pubackcomp(self, cmd):
        if self._strict_protocol:
            if self._decoded_packet['remaining_length'] != 2:
                return MQTT_ERR_PROTOCOL

        mid = struct.unpack("!H", self._decoded_packet['packet'])
        mid = mid[0]
        self._easy_log(MQTT_LOG_DEBUG, "Received "+cmd+" (Mid: "+str(mid)+")")

        self._out_message_mutex.acquire()
        for i in range(len(self._out_messages)):
            try:
                if self._out_messages[i].mid == mid:
                    # Only inform the client the message has been sent once.
                    self._callback_mutex.acquire()
                    if self.on_publish:
                        self._out_message_mutex.release()
                        self._in_callback = True
                        self.on_publish(self, self._userdata, mid)
                        self._in_callback = False
                        self._out_message_mutex.acquire()

                    self._callback_mutex.release()
                    self._out_messages.pop(i)
                    self._inflight_messages -= 1
                    if self._max_inflight_messages > 0:
                        rc = self._update_inflight()
                        if rc != MQTT_ERR_SUCCESS:
                            self._out_message_mutex.release()
                            return rc
                    self._out_message_mutex.release()
                    return MQTT_ERR_SUCCESS
            except IndexError:
                # Have removed item so i>count.
                # Not really an error.
                pass

        self._out_message_mutex.release()
        return MQTT_ERR_SUCCESS

    def _handle_on_message(self, message):
        if self.on_message is not None:
            self._callback_mutex.acquire()
            self._in_callback = True
            self.on_message(self, self._userdata, message)
            self._in_callback = False
            self._callback_mutex.release()

    def _thread_main(self):
        self.loop_forever()

    def _close_client_socket(self):
        if self._ssl:
            self._ssl.close()
            self._ssl = None
            self._sock = None
        if self._sock:
            self._sock.close()
            self._sock = None

    def _close_server_socket(self):
        # Make sure that we don't get stuck in the accept() state of the server socket
        if self._server_socket != None:
            try:
                self._server_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                # This exception is thrown for example when the socket is not even connected.
                # Anyway, we would still like to continue the shutdown process.
                pass
            self._server_socket.close()
            self._server_socket = None
            self._port = 0

    def _network_shutdown(self):
        self._close_client_socket()
        self._close_server_socket()

        if self._sockpairR:
            self._sockpairR.close()
            self._sockpairR = None
        if self._sockpairW:
            self._sockpairW.close()
            self._sockpairW = None

    @staticmethod
    def _topic_wildcard_len_check(topic):
        # Search for + or # in a topic. Return MQTT_ERR_INVAL if found.
        # Also returns MQTT_ERR_INVAL if the topic string is too long.
        # Returns MQTT_ERR_SUCCESS if everything is fine.
        if '+' in topic or '#' in topic or len(topic) == 0 or len(topic) > 65535:
            return MQTT_ERR_INVAL
        else:
            return MQTT_ERR_SUCCESS
