import tools.xi_control_channel_protocol_pb2 as xi_ccp
from tools.xi_mock_broker import mqtt_messages
import google.protobuf as protobuf
import threading

class XiControlChannel_codec_protobuf_runner:

    def __init__(self, function_map_error_codes):
        self._data_accumulator = bytes()
        self._function_map_error_codes = function_map_error_codes

    def connect(self, server_address, connect_options, connection_timeout):

        message_API_call = xi_ccp.XiClientAPI()

        if server_address[0] is not None:
            message_API_call.connect.server_address.host = server_address[0]

        message_API_call.connect.server_address.port = server_address[1]

        if connect_options.username is not None:
            message_API_call.connect.username = connect_options.username

        if connect_options.password is not None:
            message_API_call.connect.password = connect_options.password

        message_API_call.connect.mqtt_session_type = \
            xi_ccp.XiClientAPI.CLEAN_SESSION if connect_options.connect_flags & mqtt_messages.CLEAN_SESSION_FLAG else \
            xi_ccp.XiClientAPI.UNCLEAN_SESSION
        message_API_call.connect.connection_timeout = connection_timeout

        self.__log("sending connect API call = " + message_API_call.__str__() +
            ", message size in bytes = " + str(message_API_call.ByteSize()))

        self.control_channel.send(message_API_call.SerializeToString())

    def disconnect(self):
        self.__log("disconnect requested by test FW")

        message_API_call = xi_ccp.XiClientAPI()
        # could not find better way to initialize a message without payload
        message_API_call.disconnect.MergeFrom(xi_ccp.XiClientAPI.Disconnect())

        self.__log("sending api call = " + message_API_call.__str__())

        self.control_channel.send(message_API_call.SerializeToString())

    def subscribe(self, topic_and_qos_list):
        self.__log("subscribe requested by test FW: " + str(topic_and_qos_list))

        message_API_call = xi_ccp.XiClientAPI()

        for topic_and_qos in topic_and_qos_list:
            message_topic_and_qos = message_API_call.subscribe.topic_qos_list.add()
            message_topic_and_qos.topic_name = topic_and_qos[0]
            message_topic_and_qos.qos = topic_and_qos[1]

        self.control_channel.send(message_API_call.SerializeToString())

    def publish_string(self, topic, message, qos, retain):
        self.__log("publish_string requested by test FW: " + topic + ", payload = " + str(message ) )

        message_API_call = xi_ccp.XiClientAPI()

        message_API_call.publish_string.publish_common_data.topic_name = topic
        message_API_call.publish_string.payload = str(message)
        message_API_call.publish_string.publish_common_data.qos = qos
        message_API_call.publish_string.retain = retain

        self.control_channel.send(message_API_call.SerializeToString())

    def publish_binary(self, topic, message, qos, retain):
        self.__log("publish_binary requested by test FW: " + topic + ", payload = " + str(message ) )

        message_API_call = xi_ccp.XiClientAPI()

        message_API_call.publish_binary.publish_common_data.topic_name = topic
        message_API_call.publish_binary.payload = bytes(message)
        message_API_call.publish_binary.publish_common_data.qos = qos
        message_API_call.publish_binary.retain = retain

        self.control_channel.send(message_API_call.SerializeToString())

    def setup_tls(self, ca_cert_file):
        self.__log("setup_tls requested by test FW: " + ca_cert_file )

        message_FTFW_control = xi_ccp.XiClientAPI()
        message_FTFW_control.setup_tls.ca_cert_file = ca_cert_file

        self.control_channel.send(message_FTFW_control.SerializeToString())

    def handle_message(self, data):
        # protobuf decode

        self.__log( "data - " + str( data ) )

        self._data_accumulator = b"".join( [ self._data_accumulator, data ] )

        while self._data_accumulator:
            xi_client_callback = xi_ccp.XiClientCallback()

            parsed = False

            for i in range(1,len(self._data_accumulator)+1):
                try:
                    xi_client_callback.ParseFromString(self._data_accumulator[:i])
                    parsed = True
                    break
                except protobuf.message.DecodeError as decode_error:
                    self.__log("decode error exception thrown: " + str( decode_error))
                    parsed = False

            if not parsed:
                break

            # cut parsed prefix, process remaining part in next iteration
            self._data_accumulator = self._data_accumulator[xi_client_callback.ByteSize():]

            self.__log("decoded incoming data:\n" + xi_client_callback.__str__())

            # map message to API call
            if (xi_client_callback.HasField('on_connect_finish')):
                self.__log("arrived message: on_connect_finish")
                self.xi_callback_sink.on_connect_finish(
                    self._function_map_error_codes(xi_client_callback.on_connect_finish.connect_result)
                    if xi_client_callback.on_connect_finish.connect_result
                    else 0)

            if (xi_client_callback.HasField('on_disconnect')):
                self.__log("arrived message: on_disconnect")
                self.xi_callback_sink.on_disconnect(
                    self._function_map_error_codes(xi_client_callback.on_disconnect.error_code)
                    if xi_client_callback.on_disconnect.error_code
                    else 0)

            if (xi_client_callback.HasField('on_subscribe_finish')):
                self.xi_callback_sink.on_subscribe_finish(xi_client_callback.on_subscribe_finish.subscribe_result_list)

            if (xi_client_callback.HasField('on_message_received')):
                message = mqtt_messages.MQTTMessage()
                message.topic = xi_client_callback.on_message_received.topic_name
                message.qos = xi_client_callback.on_message_received.qos
                message.payload = xi_client_callback.on_message_received.payload
                self.xi_callback_sink.on_message_received(xi_client_callback.on_message_received.topic_name, message)

            if (xi_client_callback.HasField('on_publish_finish')):
                self.xi_callback_sink.on_publish_finish(xi_client_callback.on_publish_finish.return_code)

    def __getLogPrefix(self):
        return "[ PR  proto  ] [" + threading.current_thread().getName() + "]: "

    def __log(self, msg):
        print(self.__getLogPrefix() + msg)
