import xi_control_channel_protocol_pb2 as xi_ccp
from xi_mock_broker import mqtt_messages
import google.protobuf as protobuf
import threading

import os
import sys
sys.path.insert( 1, os.getcwd() + "/../../../xi_client_py/src/" )
from xiPy.xively_client import XivelyConfig

class XiControlChannel_codec_protobuf_driver:
    def __init__(self, xi_client, xi_client_connection_params):
        self._xi_apicall_sink = xi_client
        self._data_accumulator = bytes()
        self._xi_client_connection_params = xi_client_connection_params
        self.control_channel = None

        XivelyConfig.XI_MQTT_CERTS = []

    # enumerate callbacks here, each implementation will protobuf encode the callback
    def on_connect_finish(self, client, result):
        self.__log("sending callback on_connect_finish, result = " + str(result) )

        message_callback = xi_ccp.XiClientCallback()
        message_callback.on_connect_finish.connect_result = result

        self.control_channel.send(message_callback.SerializeToString())

    def on_disconnect_finish(self, client, result):
        self.__log("sending callback on_disconnect_finish, result = " + str(result))

        message_callback = xi_ccp.XiClientCallback()
        message_callback.on_disconnect.error_code = result

        self.control_channel.send(message_callback.SerializeToString())

    def on_subscribe_finish(self, client, mid, granted_qos_list):
        self.__log("sending callback on_subscribe_finish, mid, granted_qos = " + str(mid) + ", " + str(granted_qos_list))

        message_callback = xi_ccp.XiClientCallback()
        message_callback.on_subscribe_finish.subscribe_result_list.extend(granted_qos_list)

        self.control_channel.send(message_callback.SerializeToString())

    def on_message_received(self, client, message):
        self.__log("sending callback on_message_received, message = " + str(message))

        message_callback = xi_ccp.XiClientCallback()
        message_callback.on_message_received.topic_name = message.topic
        message_callback.on_message_received.qos = message.qos
        message_callback.on_message_received.payload = message.payload

        self.control_channel.send(message_callback.SerializeToString())

    def on_publish_finish(self, client, request_id):
        self.__log("sending callback on_publish_finish, request_id = " + str(request_id))

        message_callback = xi_ccp.XiClientCallback()
        message_callback.on_publish_finish.return_code = request_id

        self.control_channel.send(message_callback.SerializeToString())

    def handle_message(self, data):
        # protobuf decode

        self._data_accumulator = b"".join( [ self._data_accumulator, data ] )

        while self._data_accumulator:
            xi_client_API = xi_ccp.XiClientAPI()
            try:
                xi_client_API.ParseFromString(self._data_accumulator)
            except protobuf.message.DecodeError as decode_error:
                self.__log("decode error exception thrown: " + str( decode_error))
                break

            # cut parsed prefix, process remaining part in next iteration
            self._data_accumulator = self._data_accumulator[xi_client_API.ByteSize():]

            self.__log("decoded incoming data:\n" + xi_client_API.__str__())

            # map message to API call
            if (xi_client_API.HasField('connect')):
                XivelyConfig.XI_MQTT_HOSTS = []

                # fill up XivelyConfig hosts

                server_address = xi_client_API.connect.server_address
                XivelyConfig.XI_MQTT_HOSTS.append( (server_address.host, server_address.port, 0 != len(XivelyConfig.XI_MQTT_CERTS)) )
                # XivelyConfig.XI_MQTT_HOSTS.append( ("localhost", server_address.port, 0 != len(XivelyConfig.XI_MQTT_CERTS)) )
                XivelyConfig.XI_MQTT_WEBSOCKET_PORT = server_address.port

                self._xi_client_connection_params.username = xi_client_API.connect.username
                self._xi_client_connection_params.password = xi_client_API.connect.password
                self._xi_client_connection_params.connection_timeout = (xi_client_API.connect.connection_timeout)
                self._xi_apicall_sink.connect(self._xi_client_connection_params)

            if (xi_client_API.HasField('disconnect')):
                self._xi_apicall_sink.disconnect()

            if (xi_client_API.HasField('subscribe')):
                topic_qos_list = []
                for topic_qos in xi_client_API.subscribe.topic_qos_list:
                    topic_qos_list.append( (str(topic_qos.topic_name), topic_qos.qos) )

                self._xi_apicall_sink.subscribe(topic_qos_list)

            if (xi_client_API.HasField('publish_binary')):
                """payload must be a string, bytearray, int, float or None."""
                self._xi_apicall_sink.publish(
                    xi_client_API.publish_binary.publish_common_data.topic_name,
                    bytearray(xi_client_API.publish_binary.payload),
                    xi_client_API.publish_binary.publish_common_data.qos,
                    xi_client_API.publish_binary.retain)

            if (xi_client_API.HasField('publish_string')):
                """payload must be a string, bytearray, int, float or None."""
                self._xi_apicall_sink.publish(
                    xi_client_API.publish_string.publish_common_data.topic_name,
                    str(xi_client_API.publish_string.payload),
                    xi_client_API.publish_string.publish_common_data.qos,
                    xi_client_API.publish_string.retain)

            if (xi_client_API.HasField('setup_tls')):
                if xi_client_API.setup_tls:
                    XivelyConfig.XI_MQTT_CERTS = \
                    [ "../../../../xi_client_common/certs/test/" + xi_client_API.setup_tls.ca_cert_file ];

    def __getLogPrefix(self):
        return "[ PD  proto  ] [" + threading.current_thread().getName() + "]: "

    def __log(self, msg):
        print(self.__getLogPrefix() + msg)
