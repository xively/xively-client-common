import pytest

from tools.xi_ftest_fixture import xift
from tools.xi_ftest_fixture import sut_platform
from tools.xi_ftest_fixture import TestEssentials
from tools.xi_ftest_fixture import act

from unittest.mock import ANY, call
from tools.xi_utils import Counter, BasicMessageMatcher
from tools.xi_mock_broker import mqtt_messages
from tools.xi_mock_broker.mqtt_messages import MQTT_ERR_SUCCESS, MQTT_ERR_CONN_LOST

def publish_with_broker_disconnect_before_puback(xift, qos_level):
    ###
    # broker flow
    #   1. accept connection, send connack
    #   2. accept the control topic topic subscription
    #   3. reject publish on test topic
    broker_flow =  [ call.broker.on_client_connect(ANY, ANY),
                     call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                     call.broker.on_message(ANY,
                                            ANY,
                                            BasicMessageMatcher(TestEssentials.topic,
                                                           qos_level,
                                                           TestEssentials.payload_as_bytes ) ) ]

    #   1. accept connection, send connack
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    #  2. accept the control topic topic subscription
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                                     xift.broker.send_suback( msg_id, topics_and_qos )

    # 3. reject publish on test topic
    xift.broker.on_message.side_effect = lambda a, bb, mqtt_message: \
                                            xift.broker.trigger_shutdown()

    ###
    # client flow
    #  1. connect (automagically through act())
    #  1a. hidden, subscribe to control topic.
    #  2. on connect response, publish to topic
    #  3. on shutdown callback, stop.
    if qos_level == 0:
        client_flow = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                        call.client.on_publish_finish(ANY),
                        call.client.on_disconnect(ANY)]
    else:
        client_flow = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                        call.client.on_disconnect(ANY)]


    #  2. on connect response, subscribe to topic
    xift.client_sut.on_connect_finish.side_effect = lambda connect_response: \
                        xift.client_sut.publish_string(TestEssentials.topic, TestEssentials.payload_as_string, qos_level )

    xift.client_sut.on_publish_finish.side_effect = None

    #  3. on shutdown callback, stop.
    xift.client_sut.on_disconnect.side_effect = lambda return_code: \
                                                    xift.client_sut.stop()

    ###
    # Act
    act(xift)

    ###
    # Assert
    assert broker_flow == xift.mock_call_history_broker.method_calls
    assert client_flow == xift.mock_call_history_client.method_calls



def test_publish_PublishQoS0_DisconnectBeforePuback(xift):
    """
        Tests the correct behaviour when client publishes to a topic
            and gets disconnected

        Test scenario:
            Client Attempts to Publish to a Topic, Server disconnects

        Expectation:
            Xively Client should have its disconnected callback
            invoked
    """
    publish_with_broker_disconnect_before_puback(xift, 0)



def test_publish_PublishQoS1_DisconnectBeforePuback(xift):
    """
        Tests the correct behaviour when client publishes to a topic
            and gets disconnected before QoS 1 Puback.

        Test scenario:
            Client Attempts to Publish to a Topic, Server disconnects

        Expectation:
            Xively Client should have its disconnected callback
            invoked
    """
    publish_with_broker_disconnect_before_puback(xift, 1)



def test_publish_PublishQoS1_DisconnectAfterPuback(xift):
    """
        Tests the correct behaviour when client publishes to a topic
            and gets disconnected after QoS 1 Puback.

        Test scenario:
            Client Attempts to Publish to a Topic, Server disconnects
            after puback.

        Expectation:
            Xively Client should have its disconnected callback
            invoked
    """
    ###
    # broker flow
    #   1. accept connection, send connack
    #   2. accept the control topic topic subscription
    #   3. send puback on message
    broker_flow =  [ call.broker.on_client_connect(ANY, ANY),
                     call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                     call.broker.on_message(ANY,
                                            ANY,
                                            BasicMessageMatcher(TestEssentials.topic,
                                                                1, #qos_level
                                                                TestEssentials.payload_as_bytes) ) ]

    #   1. accept connection, send connack
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    #  2. accept the control topic topic subscription
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                xift.broker.send_suback( msg_id, topics_and_qos )

    #   3. send puback on message
    xift.broker.on_message.side_effect = lambda a, b, mqtt_message: \
                                xift.broker.send_puback(mqtt_message.mid)

    ###
    # client flow
    #  1. connect (automagically through act())
    #  1a. hidden, subscribe to control topic.
    #  2. on connect response, publish to topic
    #  3. on puback, have broker trigger shudown.
    #  3. on shutdown callback, stop.
    client_flow = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                    call.client.on_publish_finish( ANY ),
                    call.client.on_disconnect(ANY)]


    #  2. on connect response, subscribe to topic
    xift.client_sut.on_connect_finish.side_effect = lambda connect_response: \
                    xift.client_sut.publish_string(TestEssentials.topic, TestEssentials.payload_as_string, 1 )

    xift.client_sut.on_publish_finish.side_effect = lambda return_code: \
                                                    xift.broker.trigger_shutdown()

    #  3. on shutdown callback, stop.
    xift.client_sut.on_disconnect.side_effect = lambda return_code: \
                                                    xift.client_sut.stop()

    ###
    # Act
    act(xift)

    ###
    # Assert
    assert broker_flow == xift.mock_call_history_broker.method_calls
    assert client_flow == xift.mock_call_history_client.method_calls




def standard_publish_flow( xift, topic, payload, expected_payload, is_string, qos_level ):
    ###
    # broker flow
    #   1. accept connection, send connack
    #   2. accept the control topic topic subscription
    #   3. test to see if the message arrived properly formatted via Mesage Matcher
    #   4. send puback
    #   5. cleanup on client disconnect
    broker_flow = [ call.broker.on_client_connect(ANY, ANY),
                    call.broker.on_client_subscribe(ANY, ANY,
                        [(TestEssentials.control_topic_name, 1)], 0),
                    call.broker.on_message(ANY,
                                           ANY,
                                           BasicMessageMatcher(topic,
                                                               qos_level,
                                                               expected_payload ) ),
                    call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS ) ]

    #   1. accept connection, send connack
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                        xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    #  2. accept the control topic topic subscription
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                        xift.broker.send_suback( msg_id, topics_and_qos )

    #  4. send puback if qos1 or above
    def broker_on_message(a, b, mqtt_message):
        if qos_level == 0:
            pass
        else:
            xift.broker.send_puback(mqtt_message.mid)

    xift.broker.on_message.side_effect = broker_on_message

    #   5. cleanup on client disconnect
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: \
                                                      xift.broker.trigger_shutdown()


    ###
    # client flow
    #  1. connect (automagically through act())
    #   1a. hidden, subscribe to control topic.
    #  2. on connect response, publish to topic
    #  3. publish complete callback is called, shutdown.
    #  4. on shutdown callback, stop.
    client_flow = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                    call.client.on_publish_finish( ANY ),
                    call.client.on_disconnect( ANY ) ]

    def connect_finish( connect_response ):
        if is_string == True:
            xift.client_sut.publish_string(topic, payload, qos_level )
        else:
            xift.client_sut.publish_binary(topic, payload, qos_level )

    #  2. on connect response, subscribe to topic
    xift.client_sut.on_connect_finish.side_effect = connect_finish

    #  3. publish complete callback is called, shutdown.
    xift.client_sut.on_publish_finish.side_effect = lambda return_code: \
                                                        xift.client_sut.disconnect()

    #  4. on shutdown callback, stop.
    xift.client_sut.on_disconnect.side_effect = lambda return_code: xift.client_sut.stop()

    ###
    # Act
    act(xift)

    ###
    # Assert
    assert broker_flow == xift.mock_call_history_broker.method_calls
    assert client_flow == xift.mock_call_history_client.method_calls



def test_publish_PublishQoS0_SuccessfulMessageOnBrokerSide(xift):

    """
        Tests the correct behaviour when client publishes to a topic
        at QoS 0.

        Test scenario:
            Client Attempts to Publish to a Topic

        Expectation:
            Server Receives the Data in a properly formatted message.
            Everything is awesome.
    """

    qos_level = 0
    is_string = True
    standard_publish_flow( xift, TestEssentials.topic, TestEssentials.payload_as_string,
                           TestEssentials.payload_as_bytes, is_string, qos_level )


def test_publish_PublishQoS1_SuccessfulMessageOnBrokerSide(xift):

    """
        Tests the correct behaviour when client publishes to a topic
        at QoS 1.

        Test scenario:
            Client Attempts to Publish to a Topic

        Expectation:
            Server Receives the Data in a properly formatted message.
            Everything is awesome.
    """

    qos_level = 1
    is_string = True
    standard_publish_flow( xift, TestEssentials.topic, TestEssentials.payload_as_string,
                           TestEssentials.payload_as_bytes, is_string, qos_level )


def test_publish_PublishBinaryDataQoS0_SuccessfulMessageOnBrokerSide(xift):

    """
        Tests the correct behaviour when client publishes to a topic
        at QoS 0.

        Test scenario:
            Client Attempts to Publish to a Topic

        Expectation:
            Server Receives the Data in a properly formatted message.
            Everything is awesome.
    """

    qos_level = 0
    is_string = False
    standard_publish_flow( xift, TestEssentials.topic,
                           TestEssentials.binary_payload, TestEssentials.binary_payload, is_string, qos_level )


def test_publish_PublishBinaryDataQoS1_SuccessfulMessageOnBrokerSide(xift):

    """
        Tests the correct behaviour when client publishes to a topic
        at QoS 0.

        Test scenario:
            Client Attempts to Publish to a Topic

        Expectation:
            Server Receives the Data in a properly formatted message.
            Everything is awesome.
    """

    qos_level = 1
    is_string = False
    standard_publish_flow( xift, TestEssentials.topic,
                           TestEssentials.binary_payload, TestEssentials.binary_payload, is_string, qos_level )


