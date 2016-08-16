from tools.xi_ftest_fixture import xift
from tools.xi_ftest_fixture import sut_platform
from tools.xi_ftest_fixture import TestEssentials
from tools.xi_ftest_fixture import act

from tools.xi_client_error_codes import XiClientErrorCodes

from unittest.mock import ANY, call
from tools.xi_mock_broker import mqtt_messages


'''
In this testcase we test what happens when the broker unexpectedly closes it's connection
to the client after the suback message arrives to the client. (that is the one that
subscribes for the control topic)
We expect that the client calls the on_disconnect clb, with an error: MQTT_ERR_CONN_LOST.
'''
def test_disconnect_brokerClosesConnectionAfterConnectFinished_conClbCalledWithProperConnackError(xift):
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                       xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                                                         xift.broker.send_suback(msg_id, topics_and_qos)
    xift.broker.on_client_disconnect.side_effect = None


    xift.client_sut.on_connect_finish.side_effect = lambda result: \
                                               xift.broker.trigger_shutdown()
    xift.client_sut.on_disconnect.side_effect = lambda result: \
                                                       xift.client_sut.stop()

    # Act
    act(xift)

    # Assert
    expected_calls_client = [ call.client.on_disconnect(XiClientErrorCodes.CONNECTION_RESET_BY_PEER) ]
    assert expected_calls_client == xift.mock_call_history_client.method_calls[-1:]

'''
In this testcase we test what happens when the broker unexpectedly closes it's connection
to the client after the subscribe message arrives from the client. (that is the one that
subscribes for the control topic)
We expect that the client calls the on_connect_finnish clb, with an error: MQTT_ERR_CONN_LOST.
'''
def test_disconnect_brokerClosesConnectionAfterSubscribeArrives_disconnectClbWithProperConnackError(xift):

    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                       xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
        xift.broker.trigger_shutdown()
    xift.broker.on_client_disconnect.side_effect = None

    xift.client_sut.on_connect_finish.side_effect = None

    # change side effect to None as soon as control topic subscription is part of connection process of libxively
    xift.client_sut.on_disconnect.side_effect = lambda result: \
                                               xift.client_sut.stop()

    # Act
    act(xift)

    # Assert
    expected_calls_client = [ call.client.on_connect_finish(XiClientErrorCodes.SUCCESS)
                            , call.client.on_disconnect(XiClientErrorCodes.CONNECTION_RESET_BY_PEER) ]
    assert expected_calls_client == xift.mock_call_history_client.method_calls


'''
In this testcase we test what happens when the broker unexpectedly closes it's connection
to the client after it sends the CONNACK message to the client.
We expect that the client calls the on_connect_finnish clb, with an error: MQTT_ERR_CONN_LOST.
'''
def test_disconnect_brokerClosesConnectionAfterConnackMessageSent_disconnectClbCalledWithProperConnackError(xift):

    def on_client_connect(userdata, connect_options):
        xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)
        xift.broker.trigger_shutdown(True)

    xift.broker.on_client_connect.side_effect = on_client_connect
    xift.broker.on_client_disconnect.side_effect = None

    xift.client_sut.on_connect_finish.side_effect  = None

    # change side effect to None as soon as control topic subscription is part of connection process of libxively
    xift.client_sut.on_disconnect.side_effect = lambda result: \
                                               xift.client_sut.stop()

    # Act
    act(xift)

    # Assert
    expected_calls_client = [call.client.on_connect_finish(XiClientErrorCodes.SUCCESS)
                            , call.client.on_disconnect(XiClientErrorCodes.CONNECTION_RESET_BY_PEER) ]
    assert expected_calls_client == xift.mock_call_history_client.method_calls

'''
In this testcase we test what happens when the broker unexpectedly closes it's connection
to the client when it received the CONNECT message from the client.
We expect that the client calls the on_connect_finnish clb, with an error: MQTT_ERR_CONN_LOST.
'''
def test_disconnect_brokerClosesConnectionBeforeConnackMessageSent_conClbCalledWithProperConnackError(xift):
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                       xift.broker.trigger_shutdown()
    xift.broker.on_client_disconnect.side_effect = None
    xift.broker.on_client_subscribe.side_effect = None

    xift.client_sut.on_connect_finish.side_effect  = lambda result: \
                                               xift.client_sut.stop()

# Act
    act(xift)

    # Assert
    expected_calls_client = [ call.client.on_connect_finish(XiClientErrorCodes.CONNECTION_RESET_BY_PEER) ]
    assert expected_calls_client == xift.mock_call_history_client.method_calls[:1]

