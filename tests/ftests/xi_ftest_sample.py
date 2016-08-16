import pytest
from tools.xi_ftest_fixture import xift
from tools.xi_ftest_fixture import sut_platform
from tools.xi_ftest_fixture import TestEssentials
from tools.xi_ftest_fixture import act

from unittest.mock import ANY, call
from tools.xi_utils import Counter
from tools.xi_utils import Counter, BasicMessageMatcher
from tools.xi_mock_broker import mqtt_messages
from tools.xi_mock_broker.mqtt_messages import MQTT_ERR_SUCCESS
from tools.xi_client_error_codes import XiClientErrorCodes
from tools.xi_client_settings import XiClientPlatform

#################
# Test cases    #
#################

# Test where client can connect successfully
def test_tls_connect_successfully(xift):
    # Arrange
    xift.client_sut.on_connect_finish.side_effect = lambda connect_res: xift.client_sut.disconnect()
    xift.client_sut.on_disconnect.side_effect = lambda return_code: xift.client_sut.stop()

    def validate_connection(userdata, connect_options):

        def assert_connect_options():
            assert connect_options.client_id.decode("utf-8") == xift.connect_options.username
            assert mqtt_messages.CLEAN_SESSION_FLAG \
                | mqtt_messages.USERNAME_FLAG \
                | mqtt_messages.PASSWORD_FLAG == connect_options.connect_flags

        xift._task_queue.put(assert_connect_options)

        xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    xift.broker.on_client_connect.side_effect = validate_connection
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: \
                                                xift.broker.trigger_shutdown()
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                                    xift.broker.send_suback(msg_id, topics_and_qos)

    xift.connect_options.connect_flags = xift.connect_options.connect_flags | mqtt_messages.CLEAN_SESSION_FLAG

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [(TestEssentials.control_topic_name, 1)], 0),
                              call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS)]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(ANY)]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_device_status_data_publish_on_boot(xift):
    if xift.sut_platform == XiClientPlatform.C:
        pytest.xfail("feature can be activated only for python clients")

    # Arrange
    xift.client_sut.on_connect_finish.side_effect = lambda connect_res: xift.client_sut.disconnect()
    xift.client_sut.on_disconnect.side_effect = lambda return_code: xift.client_sut.stop()
    xift.client_sut.on_publish_finish.side_effect = None

    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: \
                                                xift.broker.trigger_shutdown()
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                                    xift.broker.send_suback(msg_id, topics_and_qos)

    xift.broker.on_message.side_effect = None # no need to puback for now

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [(TestEssentials.control_topic_name, 1)], 0),
                              call.broker.on_message(ANY, ANY, BasicMessageMatcher("device-status", 0, None )),
                              call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS)]

    expected_calls_client = [ call.client.on_publish_finish(ANY),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(ANY)]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls


def test_clientSidePublish_messageArrivesAtBroker(xift):
    #Arrange
    xift.client_sut.on_connect_finish.side_effect = lambda connect_res: \
                          xift.client_sut.publish_binary(TestEssentials.topic, TestEssentials.binary_payload, 1)
    xift.client_sut.on_publish_finish.side_effect = lambda request_id: xift.client_sut.disconnect()
    xift.client_sut.on_disconnect.side_effect = lambda return_code: xift.client_sut.stop()

    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                  xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: \
                                                  xift.broker.trigger_shutdown()

    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                                    xift.broker.send_suback(msg_id, topics_and_qos)
    xift.broker.on_message.side_effect = lambda a, b, mqtt_message: \
                                          xift.broker.send_puback(mqtt_message.mid)

    #Act
    act(xift)

    #Assert
    class MessageMatcher(mqtt_messages.MQTTMessage):
        def __init__(self):
            super(MessageMatcher, self).__init__()

        def __eq__(self, other):
            return TestEssentials.binary_payload == other.payload and 1 == other.qos

    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [(TestEssentials.control_topic_name, 1)], 0),
                              call.broker.on_message(ANY, ANY, MessageMatcher()),
                              call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS)]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_publish_finish(ANY),
                              call.client.on_disconnect(ANY)]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls


# Test where broker delivers 5 messages to the client (which has not subscribed before to that topic).
def test_receive_5_unsubscribed_messages(xift):
    if xift.sut_platform == XiClientPlatform.C:
        pytest.xfail("This test require XivelyC library to have handle for receiving unsubscribed messages")

    # Arrange
    def deliver_5(result):
        for i in range(5):
            xift.broker.publish(TestEssentials.topic, TestEssentials.payload_as_string)

    def collect_5_and_exit():
        counter = Counter()
        def collect_all(topic, message):
            counter.inc()
            # We can avoid using matchers by asserting here on the message.
            assert TestEssentials.topic == message.topic
            assert TestEssentials.payload_as_bytes == message.payload
            assert 0 == message.qos
            if counter.is_at(5):
                xift.client_sut.disconnect()

        return collect_all

    xift.client_sut.on_connect_finish.side_effect = deliver_5
    xift.client_sut.on_disconnect.side_effect = lambda result: xift.client_sut.stop()
    xift.client_sut.on_message_received.side_effect = collect_5_and_exit()

    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                    xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)
    xift.broker.on_client_disconnect.side_effect = lambda a, b, c: xift.broker.trigger_shutdown()
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                                    xift.broker.send_suback(msg_id, topics_and_qos)

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [(TestEssentials.control_topic_name, 1)], 0),
                              call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS)]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_message_received(ANY, ANY),
                              call.client.on_message_received(ANY, ANY),
                              call.client.on_message_received(ANY, ANY),
                              call.client.on_message_received(ANY, ANY),
                              call.client.on_message_received(ANY, ANY),
                              call.client.on_disconnect(MQTT_ERR_SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls


# Test where client received 5 subscribed messages
def test_receive_5_subscribed_messages(xift):
    # Arrange
    def deliver_5(userdata, msg_id, topics_and_qos, dup):
        xift.broker.send_suback(msg_id, topics_and_qos)
        if [(TestEssentials.topic_as_bytes, 0)] == topics_and_qos :
            # Deliver 5 messages to the client
            for i in range(5):
                xift.broker.publish(TestEssentials.topic, TestEssentials.payload_as_string)

    def collect_5_and_exit():
        counter = Counter()
        def collect_all(topic, message):
            counter.inc()
            if counter.is_at(5):
                xift.client_sut.disconnect()
        return collect_all

    xift.client_sut.on_connect_finish.side_effect = lambda connect_response: \
                                                        xift.client_sut.subscribe([[TestEssentials.topic, 0]])
    xift.client_sut.on_disconnect.side_effect = lambda return_code: xift.client_sut.stop()
    xift.client_sut.on_subscribe_finish.side_effect = None
    xift.client_sut.on_message_received.side_effect = collect_5_and_exit()

    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                    xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)
    xift.broker.on_client_subscribe.side_effect = deliver_5
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: xift.broker.trigger_shutdown()

    # Act
    act(xift)

    # Assert
    class MessageMatcher(mqtt_messages.MQTTMessage):
        def __init__(self):
            super(MessageMatcher, self).__init__()

        def __eq__(self, other):
            return TestEssentials.payload_as_bytes == other.payload and 0 == other.qos

    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [(TestEssentials.control_topic_name, 1)], 0),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [(TestEssentials.topic_as_bytes, 0)], 0),
                              call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS)]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_subscribe_finish([0]),
                              # 5 times
                              call.client.on_message_received(TestEssentials.topic, MessageMatcher()),
                              call.client.on_message_received(TestEssentials.topic, MessageMatcher()),
                              call.client.on_message_received(TestEssentials.topic, MessageMatcher()),
                              call.client.on_message_received(TestEssentials.topic, MessageMatcher()),
                              call.client.on_message_received(TestEssentials.topic, MessageMatcher()),

                              call.client.on_disconnect(MQTT_ERR_SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

####################
# TLS test cases   #
####################


# Test connection via TLS, but the cert is expired
def test_tls_connect_with_expired_cert(xift):

    def client_on_connect_finish( errorcode ):
        xift.client_sut.stop()
        xift.broker.trigger_shutdown()

    # Arrange
    certfile = "self-signed-expired-cert.pem"

    xift.client_sut.setup_tls(certfile)
    xift.broker.setup_tls("../../../xi_client_common/certs/test/" + certfile,
                          "../../../xi_client_common/certs/test/" + "self-signed-expired-key.pem")

    xift.client_sut.on_connect_finish.side_effect = client_on_connect_finish

    # Act
    act(xift, setup_default_cert=False)

    # Assert
    expected_calls_client = [ call.client.on_connect_finish(XiClientErrorCodes.CERTERROR) ]

    assert expected_calls_client == xift.mock_call_history_client.method_calls


# Test connection via TLS, but the cert domain is not what we expect
def test_tls_connect_with_bad_domain(xift):

    # Arrange
    certfile = "self-signed-bad-domain-cert.pem"

    xift.client_sut.setup_tls(certfile)
    xift.broker.setup_tls("../../../xi_client_common/certs/test/" + certfile,
                          "../../../xi_client_common/certs/test/" + "self-signed-bad-domain-key.pem")

    #xift.broker.on_ssl_error = lambda broker, username, ssl_err: print("Broker SSL error!!!")
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: xift.broker.trigger_shutdown()

    def client_on_connect_finish(result):
        # problem: broker shutdown is here too because in case of py2 Client broker does not call its on_client_disconnect
        xift.broker.trigger_shutdown()
        xift.client_sut.stop()

    xift.client_sut.on_connect_finish.side_effect = client_on_connect_finish

    # Act
    act(xift, setup_default_cert=False)

    # Assert
    expected_calls_client = [ call.client.on_connect_finish(XiClientErrorCodes.SSLERROR) ]

    assert expected_calls_client == xift.mock_call_history_client.method_calls
