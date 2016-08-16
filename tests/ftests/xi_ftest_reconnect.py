from tools.xi_ftest_fixture import xift
from tools.xi_ftest_fixture import sut_platform
from tools.xi_ftest_fixture import TestEssentials
from tools.xi_ftest_fixture import act

from unittest.mock import ANY, call
from tools.xi_utils import Counter
from tools.xi_mock_broker import mqtt_messages
from tools.xi_mock_broker.mqtt_messages import MQTT_ERR_SUCCESS

'''
Client connects and disconnects 3 times to the same broker
'''
def test_reconnect_clientDisconnectsAndReconnects3Times_3SuccessfulConnect(xift):
    # Arrange

    def on_disconnect_connect_twice_then_stop():
        counter = Counter()
        def on_disconnect_connect_twice_then_stop_impl(return_code):
            counter.inc()
            if counter.is_at(3):
                xift.client_sut.stop()
            else:
                xift.client_sut.connect(xift.broker.bind_address, xift.connect_options, TestEssentials.connection_timeout)

        return on_disconnect_connect_twice_then_stop_impl

    xift.client_sut.on_disconnect.side_effect = on_disconnect_connect_twice_then_stop()
    xift.client_sut.on_connect_finish.side_effect = lambda connect_result: \
                                                           xift.client_sut.disconnect()

    def on_client_disconnect_shutdown_after_third():
        counter = Counter()
        def on_third_call_shutdown(broker, userdata, result_code):
            counter.inc()
            if counter.is_at(3):
                xift.broker.trigger_shutdown()
        return on_third_call_shutdown

    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                       xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)
    xift.broker.on_client_disconnect.side_effect = on_client_disconnect_shutdown_after_third()
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                                         xift.broker.send_suback(msg_id, topics_and_qos)

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [(TestEssentials.control_topic_name, 1)], 0),
                              call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [(TestEssentials.control_topic_name, 1)], 0),
                              call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [(TestEssentials.control_topic_name, 1)], 0),
                              call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(MQTT_ERR_SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(MQTT_ERR_SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(MQTT_ERR_SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls
