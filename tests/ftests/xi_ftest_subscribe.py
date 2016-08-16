import pytest
from tools.xi_ftest_fixture import xift
from tools.xi_ftest_fixture import sut_platform
from tools.xi_ftest_fixture import TestEssentials
from tools.xi_ftest_fixture import act


from unittest.mock import ANY, call
from tools.xi_utils import Counter
from tools.xi_mock_broker import mqtt_messages
from tools.xi_mock_broker.mqtt_messages import MQTT_ERR_SUCCESS, MQTT_ERR_CONN_LOST
from tools.xi_utils import Counter, BasicMessageMatcher


def test_subcribe_subackFailure_conClbCalledWithProperSubackError(xift):

    """
        Tests the correct behaviour when server sends refuse in response to
        SUBSCRIBE request

        Test scenario:
            Client Attempts to Subscribe to a Topic, Server sends a SUBACK with error code 0x80.

        Expectation:
            Client should invoke subscription callback with an apropriate
            error state set
    """

    ###
    # broker flow
    #   1. accept connection, send connack
    #   2. accept the control topic topic subscription
    #   3. deny any other subscription
    #   4. Cleanup on Disconnect
    broker_flow = [ call.broker.on_client_connect(ANY, ANY),
                    call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                    call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                    call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS)]

    def broker_on_client_subscribe( userdata, msg_id, topics_and_qos, dup ):
        subscribe_results = []
        for index, t in enumerate(topics_and_qos):
            subscribe_results.append( [ t[0], t[1] ] )
            if t[0] != TestEssentials.control_topic_name:
                subscribe_results[index] = [ t[0], 0x80 ]
        xift.broker.send_suback( msg_id, subscribe_results )

    #   1. accept connection, send connack
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                    xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)
    #   2. accept the control topic topic subscription
    #   3. deny any other subscription
    xift.broker.on_client_subscribe.side_effect = broker_on_client_subscribe

    #   4. Cleanup on Disconnect
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: \
                                                xift.broker.trigger_shutdown()

    ###
    # client flow
    #  1. connect (automagically through act())
    #  1a. hidden, subscribe to control topic.
    #  2. on connect response, subscribe to topic
    #  3. monitor subscription callback, check for error state
    #  4. on subscribe callback, shutdown connection
    #  5. on shutdown callback, stop.

    client_flow = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                    call.client.on_subscribe_finish([0x80]), # 3. monitor subscription callback, check for error state
                    call.client.on_disconnect(ANY)]

    #  2. on connect response, subscribe to topic
    xift.client_sut.on_connect_finish.side_effect = lambda connect_response: \
                                                        xift.client_sut.subscribe([[TestEssentials.topic, 1]])

    #  4. on subscribe callback, shutdown connection
    xift.client_sut.on_subscribe_finish.side_effect = lambda granted_access_list: xift.client_sut.disconnect()

    #  5. on shutdown callback, stop.
    xift.client_sut.on_disconnect.side_effect = lambda return_code: xift.client_sut.stop()

    ###
    # Act
    act(xift)

    ###
    # Assert
    assert broker_flow == xift.mock_call_history_broker.method_calls
    assert client_flow == xift.mock_call_history_client.method_calls


def test_subscribe_subscribeIncomingPublishQoS0_subscribeClbCalledSuccess(xift):

    """
        Tests the correct behaviour when client subscribes to a topic and
        an incoming message arrives on the topic.

        Test scenario:
            Client Attempts to Subscribe to a Topic, Server sends a message
            on topic after SUBACK

        Expectation:
            Client should invoke subscription callback
    """

    ###
    # broker flow
    #   1. accept connection, send connack
    #   2. accept the control topic topic subscription
    #   3. accept the standard topic subscription, check for QoS 0
    #   4. Cleanup on Disconnect
    broker_flow =  [ call.broker.on_client_connect(ANY, ANY),
                     call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                     #   3. check for QoS 0
                     call.broker.on_client_subscribe(ANY, ANY,
                        [ (TestEssentials.topic_as_signed_chars, 0 ) ], 0 ),
                     call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS) ]

    #   1. accept connection, send connack
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                    xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    #   2. accept the control topic topic subscription
    #   3. accept the standard topic subscription,
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                                    xift.broker.send_suback( msg_id, topics_and_qos )


    #   4. Cleanup on Disconnect
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: \
                                                xift.broker.trigger_shutdown()

    ###
    # client flow
    #  1. connect (automagically through act())
    #  1a. hidden, subscribe to control topic.
    #  2. on connect response, subscribe to topic
    #  3. subscription callback invoked, broker to publish to topic client subscribed to.
    #  4. on message callback, validate message, shutdown connection
    #  5. on shutdown callback, stop.

    # Validates that the message parameters are what we expect to recieve on the client.
    client_flow = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                    call.client.on_subscribe_finish( [ANY] ),      # 3. subscription callback invoked
                    call.client.on_message_received( ANY,          # 4. on message callback validate message
                                                     BasicMessageMatcher(TestEssentials.topic,
                                                                         0, #qos_level
                                                                         TestEssentials.payload_as_bytes ) ),
                    call.client.on_disconnect(ANY) ]


    #  2. on connect response, subscribe to topic
    xift.client_sut.on_connect_finish.side_effect = lambda connect_response: \
                                                        xift.client_sut.subscribe([[TestEssentials.topic, 0]])

    #  3. subscription callback invoked, broker to publish to topic client subscribed to.
    xift.client_sut.on_subscribe_finish.side_effect = lambda granted_access_list: \
                                                        xift.broker.publish(TestEssentials.topic, TestEssentials.payload_as_string)

    #  4. on message callback, ..., shutdown connection
    xift.client_sut.on_message_received.side_effect = lambda topic, message: \
                                                        xift.client_sut.disconnect()

    #  5. on shutdown callback, stop.
    xift.client_sut.on_disconnect.side_effect = lambda return_code: xift.client_sut.stop()

    ###
    # Act
    act(xift)

    ###
    # Assert
    assert broker_flow == xift.mock_call_history_broker.method_calls
    assert client_flow == xift.mock_call_history_client.method_calls

def subscribeAtQoS_BrokerPublishMessageAtQoS_Runner(xift, subscribe_qos, publish_qos ):
    """
        Tests the correct behaviour when client subscribes to a topic at
        variable QoS levels and Broker Publishes to the topic at variable QoS levels.

        Test ensures that the various QoS levels reach the broker correctly
        and are correctly provided to the callbacks to the client application
    """
    ###
    # broker flow
    #   1. accept connection, send connack
    #   2. accept the control topic topic subscription
    #   3. accept the standard topic subscription, check for 'subscribe_qos'
    #   4. Cleanup on Disconnect
    broker_flow = [ call.broker.on_client_connect(ANY, ANY),
                    #   2. accept the control topic topic subscription
                    call.broker.on_client_subscribe(ANY, ANY,
                        [(TestEssentials.control_topic_name, 1)], 0),
                    #   3. accept the standard topic subscription, check for 'subscribe_qos'
                    call.broker.on_client_subscribe(ANY, ANY,
                        [(TestEssentials.topic_as_signed_chars, subscribe_qos)], 0),
                    call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS)]

    # 1. accept connection, send connack
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                  xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    #   2. accept the control topic topic subscription
    #   3. accept the standard topic subscription
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                                    xift.broker.send_suback( msg_id, topics_and_qos )

    #   4. Cleanup on Disconnect
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: \
                                                  xift.broker.trigger_shutdown()

    ###
    # client flow
    #  1. connect (automagically through act())
    #  1a. hidden, subscribe to control topic.
    #  2. on connect response, subscribe to topic
    #  3. subscription callback invoked, broker to publish to topic client subscribed to.
    #  4. on message callback, validate message, shutdown connection
    #  5. on shutdown callback, stop.

    # Validates that the message parameters are what we expect to recieve on the client.
    client_flow = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                    call.client.on_subscribe_finish([ANY]),
                    #  4. on message callback, validate message,
                    call.client.on_message_received(ANY,
                                                    BasicMessageMatcher(TestEssentials.topic,
                                                                         publish_qos,
                                                                         TestEssentials.payload_as_bytes ) ),
                    call.client.on_disconnect(ANY)]

    #2. on connect response, subscribe to topic
    xift.client_sut.on_connect_finish.side_effect = lambda connect_res: \
                        xift.client_sut.subscribe([[TestEssentials.topic, subscribe_qos]])

    #  3. subscription callback invoked, broker publish to topic client subscribed to.
    xift.client_sut.on_subscribe_finish.side_effect = lambda granted_access_list: \
                        xift.broker.publish( TestEssentials.topic, TestEssentials.payload_as_string, publish_qos )

    #  4. on message callback, shutdown connection
    xift.client_sut.on_message_received.side_effect = lambda topic, message: \
                        xift.client_sut.disconnect()

    #  5. on shutdown callback, stop.
    xift.client_sut.on_disconnect.side_effect = lambda return_code: xift.client_sut.stop()

    ##
    #Act
    act(xift)

    ##
    #Assert
    assert client_flow == xift.mock_call_history_client.method_calls
    assert broker_flow == xift.mock_call_history_broker.method_calls

def test_subscribe_subscribeQoS0_IncomingPublishQoS0__subscribe_and_on_messageClbCalledSuccess(xift):
    """
        Tests the correct behaviour when client subscribes to a topic at QoS 0
            and publishes to the topic on QoS 0

        Test scenario:
            Client Attempts to Subscribe to a Topic and the Broker Publishes to it.

        Expectation:
            Client should invoke message arrives callback with the correct message QoS value
            for the associated topic.
    """

    subscribe_qos = 0
    publish_qos = 0
    subscribeAtQoS_BrokerPublishMessageAtQoS_Runner(xift, subscribe_qos, publish_qos)


def test_subscribe_subscribeQoS1_IncomingPublishQoS0__subscribe_and_on_messageClbCalledSuccess(xift):
    """
        Tests the correct behaviour when client subscribes to a topic at QoS 1
            and Broker publishes to the topic on QoS 0

        Test scenario:
            Client Attempts to Subscribe to a Topic and Broker Publishes to it.

        Expectation:
            Client should invoke message arrives callback with the correct message QoS value
            for the associated topic.
    """

    subscribe_qos = 1
    publish_qos = 0
    subscribeAtQoS_BrokerPublishMessageAtQoS_Runner(xift, subscribe_qos, publish_qos)


def test_subscribe_subscribeQoS1_IncomingPublishQoS1__subscribe_and_on_messageClbCalledSuccess(xift):
    """
        Tests the correct behaviour when client subscribes to a topic at QoS 1
        and Broker publishes to the topic on QoS 1

        Test scenario:
            Client Attempts to Subscribe to a Topic and Broker Publishes to it.

        Expectation:
            Client should invoke message arrives callback with the correct message QoS value
            for the associated topic.
    """

    subscribe_qos = 1
    publish_qos = 1
    subscribeAtQoS_BrokerPublishMessageAtQoS_Runner(xift, subscribe_qos, publish_qos)

def test_subscribe_subscribe_DisconnectBeforeSuback_on_disconnectClbCalledSuccess(xift):
    """
        Tests the correct behaviour when client subscribes to a topic
        and the broker disonnects the connection before the suback is sent.

        Test scenario:
            Client Attempts to Subscribe to a Topic, broker disconects before suback.

        Expectation:
            Client should invoke disconnect callback.
    """
    ###
    # broker flow
    #   1. accept connection, send connack
    #   2. accept the control topic topic subscription
    #   3. on client subscription request, shutdown the broker.
    broker_flow = [ call.broker.on_client_connect(ANY, ANY),
                    call.broker.on_client_subscribe(ANY, ANY,
                        [(TestEssentials.control_topic_name, 1)], 0),
                    call.broker.on_client_subscribe(ANY, ANY,
                        [(TestEssentials.topic_as_signed_chars, 1)], 0) ]

    # 1. accept connection, send connack
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                  xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    #   2. accept the control topic topic subscription
    #   3. on client subscription request, shutdown the broker.
    def broker_on_client_subscribe( userdata, msg_id, topics_and_qos, dup ):
        for t in topics_and_qos:
            if t[0] != TestEssentials.control_topic_name:
                xift.broker.trigger_shutdown()
        xift.broker.send_suback( msg_id, topics_and_qos )

    xift.broker.on_client_subscribe.side_effect = broker_on_client_subscribe

    ###
    # client flow
    #  1. connect (automagically through act())
    #  1a. hidden, subscribe to control topic.
    #  2. on connect response, subscribe to topic
    #  3. on disconnect callback invoked, cleanup and shutdown.
    client_flow = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                    call.client.on_disconnect(ANY)]

    #2. on connect response, subscribe to topic
    xift.client_sut.on_connect_finish.side_effect = lambda connect_res: \
                          xift.client_sut.subscribe([[TestEssentials.topic, 1]])

    #  3. on disconnect callback invoked, cleanup and shutdown.
    xift.client_sut.on_disconnect.side_effect = lambda return_code: xift.client_sut.stop()

    ##
    #Act
    act(xift)

    ##
    #Assert
    assert client_flow == xift.mock_call_history_client.method_calls
    assert broker_flow == xift.mock_call_history_broker.method_calls


def test_subscribe_subscribe_DisconnectAfterSuback_on_disconnectClbCalledSuccess(xift):
    """
        Tests the correct behaviour when client subscribes to a topic
        and the Broker disonnects the connection after the suback is sent.

        Test scenario:
            Client Attempts to Subscribe to a Topic, Broker disconects before suback.

        Expectation:
            Client should invoke disconnect callback.
    """
    ###
    # broker flow
    #   1. accept connection, send connack
    #   2. accept the control topic topic subscription
    #   3. on client subscription request, shutdown the broker.
    broker_flow = [ call.broker.on_client_connect(ANY, ANY),
                    call.broker.on_client_subscribe(ANY, ANY,
                        [(TestEssentials.control_topic_name, 1)], 0),
                    call.broker.on_client_subscribe(ANY, ANY,
                        [(TestEssentials.topic_as_signed_chars, 1)], 0) ]

    # 1. accept connection, send connack
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                  xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    #   2. accept the subscriptions
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                                    xift.broker.send_suback( msg_id, topics_and_qos )

    ###
    # client flow
    #  1. connect (automagically through act())
    #  1a. hidden, subscribe to control topic.
    #  2. on connect response, subscribe to topic
    #  3. on disconnect callback invoked, cleanup and shutdown.
    #  4. on disconnect callback invoked, cleanup and shutdown.
    client_flow = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                    call.client.on_subscribe_finish([ANY]),
                    call.client.on_disconnect(ANY)]

    # 2. on connect response, subscribe to topic
    xift.client_sut.on_connect_finish.side_effect = lambda connect_res: \
                          xift.client_sut.subscribe([[TestEssentials.topic, 1]])

    #  3. client suback, disconnect
    xift.client_sut.on_subscribe_finish.side_effect =  lambda granted_access_list: xift.broker.trigger_shutdown()

    #  4. on disconnect callback invoked, cleanup and shutdown.
    def client_on_disconnect( return_code ):
        xift.client_sut.stop()

    xift.client_sut.on_disconnect.side_effect = client_on_disconnect


    ##
    #Act
    act(xift)

    ##
    #Assert
    assert client_flow == xift.mock_call_history_client.method_calls
    assert broker_flow == xift.mock_call_history_broker.method_calls


