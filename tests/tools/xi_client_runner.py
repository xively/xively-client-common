from tools.xi_mock_broker.xi_mock_broker import cert_reqs, tls_version

import threading
from threading import Thread
from time import sleep

class XiClientRunner:

    def __init__(self, driver_starter, control_channel_codec, control_channel_transport):

        self._driver_starter = driver_starter
        self._control_channel_codec = control_channel_codec
        self._control_channel_transport = control_channel_transport

        self._control_channel_transport.create_listensocket()
        self._driver_starter.start_driver(self._control_channel_transport.hostaddr, self._control_channel_transport.port)
        self._control_channel_transport.wait_for_connection()

    def stop(self):
        self._control_channel_transport.stop()

    def join(self, timeout):
        return self._control_channel_transport.join(timeout)

    def connect(self, server_address, connect_options, connection_timeout):
        self._control_channel_codec.connect(server_address, connect_options, connection_timeout)

    def on_connect_finish(self, connect_response):
        pass

    def disconnect(self):
        self._control_channel_codec.disconnect()

    def on_disconnect(self, return_code):
        pass

    def subscribe(self, topic_list):
        self._control_channel_codec.subscribe(topic_list)

    def on_subscribe_finish(self, granted_access_list):
        pass

    def publish_string(self, topic, message=None, qos=0, retain_flag=False):
        self._control_channel_codec.publish_string(topic, message, qos, retain_flag)

    def publish_binary(self, topic, message=None, qos=0, retain_flag=False):
        self._control_channel_codec.publish_binary(topic, message, qos, retain_flag)

    def publish_timeseries(self, topic, value=0.0, qos=0 ):
        self._control_channel_codec.publish_timeseries(topic, message, value, qos)

    def publish_formatted_timeseries(self, topic, time=0, category=None, string_value=None, numeric_value=0.0, qos=0):
        self._control_channel_codec.publish_formatted_timeseries(topic, time, category, string_value, numeric_value, qos)

    def on_publish_finish(self, return_code):
        pass

    def on_message_received(self, topic, message):
        pass

    def setup_tls(self, ca_cert_file):
        self._driver_starter.prepare_environment(ca_cert_file)
        self._control_channel_codec.setup_tls(ca_cert_file)
