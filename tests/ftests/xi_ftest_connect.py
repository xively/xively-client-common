import pytest
from tools.xi_ftest_fixture import xift
from tools.xi_ftest_fixture import sut_platform
from tools.xi_ftest_fixture import TestEssentials
from tools.xi_ftest_fixture import act

from unittest.mock import ANY, call
from tools.xi_utils import Counter
from tools.xi_mock_broker import mqtt_messages
from tools.xi_mock_broker.mqtt_messages import MQTT_ERR_SUCCESS, MQTT_ERR_CONN_LOST
from tools.xi_client_error_codes import XiClientErrorCodes
from tools.xi_client_settings import XiClientPlatform

class ServerConnackClientOnConnectFinish:
    def __init__(self, server_connack, client_on_connect_finish):
        self.server_connack = server_connack
        self.client_on_connect_finish = client_on_connect_finish

@pytest.fixture(scope="function"
                ,params=[ ServerConnackClientOnConnectFinish(
                                mqtt_messages.CONNACK_REFUSED_NOT_AUTHORIZED,
                                XiClientErrorCodes.MQTT_NOT_AUTHORISED ),
                          ServerConnackClientOnConnectFinish(
                                mqtt_messages.CONNACK_REFUSED_PROTOCOL_VERSION,
                                XiClientErrorCodes.MQTT_PROTOCOL_VERSION ),
                          ServerConnackClientOnConnectFinish(
                                mqtt_messages.CONNACK_REFUSED_SERVER_UNAVAILABLE,
                                XiClientErrorCodes.MQTT_SERVER_UNAVAILABLE ),
                          ServerConnackClientOnConnectFinish(
                                mqtt_messages.CONNACK_REFUSED_IDENTIFIER_REJECTED,
                                XiClientErrorCodes.MQTT_IDENTIFIER_REJECTED ),
                          ServerConnackClientOnConnectFinish(
                                mqtt_messages.CONNACK_REFUSED_BAD_USERNAME_PASSWORD,
                                XiClientErrorCodes.MQTT_BAD_USERNAME_OR_PASSWORD )
                        ]
                ,ids=[  "CONNACK_REFUSED_NOT_AUTHORIZED"
                      , "CONNACK_REFUSED_PROTOCOL_VERSION"
                      , "CONNACK_REFUSED_SERVER_UNAVAILABLE"
                      , "CONNACK_REFUSED_IDENTIFIER_REJECTED"
                      , "CONNACK_REFUSED_BAD_USERNAME_PASSWORD"
                      ])
def mqtt_connect_setup(request):
    return request.param


def test_connect_badDomain_conClbCalledWithError(xift):
    """
        Tests the behaviour of the client when the client tries to connect
        to an nonexisting domain name.

        Test scenario:
            Make the client to connect to a given domain that does not exists

        Expectation:
            Client should invoke connection finished callback with one of the error
            related to a socket or gethostbyname or socket connection error
    """

    def validate_params( state ):
        xift.client_sut.stop()
        xift.broker.trigger_shutdown()

        assert state in [  XiClientErrorCodes.SOCKET_ERROR
                         #, XiClientErrorCodes.XI_SOCKET_GETHOSTBYNAME_ERROR
                         #, XiClientErrorCodes.XI_SOCKET_CONNECTION_ERROR
                         ]

    xift.client_sut.on_connect_finish.side_effect = validate_params

    act(xift,endpoint=("non_existing_domain.com",666))


def test_connect_connectionRefused_conClbCalledWithProperConnackError(xift, mqtt_connect_setup):

    """
        Tests the correct behaviour whenever server sends refuse in response to
        CONNECT msg

        Test scenario:
            Every connect attempt will be treated same way, server will send
            CONNACK with one of possible connack error codes

        Expectation:
            Client should invoke connection finished callback with an apropriate
            error state set
    """
    # broker on connection just say that the credentials are wrong
    def broker_on_client_connect( userdata, connect_options ):
        xift.broker.send_connack( mqtt_connect_setup.server_connack )
        #xift.broker.trigger_shutdown()

    # client when connection finished just stops
    def client_on_connect_finish( connection_res ):
        xift.client_sut.stop()

    # brokers side effects
    xift.broker.on_client_connect.side_effect = broker_on_client_connect
    xift.broker.on_client_disconnect.side_effect = lambda value: xift.broker.trigger_shutdown()

    # client side effects
    xift.client_sut.on_connect_finish.side_effect = client_on_connect_finish

    # run
    act(xift)

    # expectations
    expected_calls_broker = [ call.broker.on_client_connect(ANY,ANY)
                            , call.broker.on_client_disconnect(ANY, ANY, 1) ]

    expected_calls_client = [ call.client.on_connect_finish( mqtt_connect_setup.client_on_connect_finish ) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls


def test_connect_connectionTimeout_conClbCalledWithTimeoutState(xift):
    """
        Tests if the connection operation is timed out properly

        Test scenario:
            Make the server to receive the CONNECT msg from the client
            but don't send the CONNACK response

        Expectations:
            Client should close the connection and invoke the on_connect_finish
            callback connection using timeout error state within
            apropriate amount of time defined via the connection settings.
    """

    xift.client_sut.on_connect_finish.side_effect = \
        lambda connect_res: xift.client_sut.stop()

    # Remove side effect so that it won't raise exception on usage.
    xift.client_sut.on_disconnect.side_effect = None

    xift.broker.on_client_connect.side_effect = None
    xift.broker.on_client_subscribe.side_effect = None
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: \
                                                    xift.broker.trigger_shutdown()

    # Set the connection timeout based on the actual test value
    TestEssentials.connection_timeout = 2

    # Sanity checks
    assert TestEssentials.connection_timeout > 0
    assert TestEssentials.test_timeout > TestEssentials.connection_timeout

    # Act
    act(xift)

    # Assert parameters
    expected_calls_broker = [  call.broker.on_client_connect(ANY, ANY)
                             , call.broker.on_client_disconnect(ANY, ANY, 1) ]
    expected_calls_client = [ call.client.on_connect_finish(XiClientErrorCodes.TIMEOUT)]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_connect_connectionTimeout_conClbCalledWithControlTopicError(xift):
    """
        Tests if the connection operation is timed out properly after CONNACK is sent by
        the broker, but no SUBACK is sent in response to control topic subscription

        Test scenario:
            Make the server to receive the CONNECT msg from the client
            send the CONNACK response but don't send SUBACK response

        Expectations:
            Client should close the connection and invoke the on_connect_finish
            callback connection using control topic error state within
            appropriate amount of time defined via the connection settings.
    """

    xift.client_sut.on_connect_finish.side_effect = \
        lambda connect_res: xift.client_sut.stop()

    # Remove side effect so that it won't raise exception on usage.
    xift.client_sut.on_disconnect.side_effect = None

    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                                                    xift.broker.send_connack( mqtt_messages.CONNACK_ACCEPTED )
    xift.broker.on_client_subscribe.side_effect = None
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: \
                                                    xift.broker.trigger_shutdown()

    # Set the connection timeout based on the actual test value
    TestEssentials.connection_timeout = 2

    # Sanity checks
    assert TestEssentials.connection_timeout > 0
    assert TestEssentials.test_timeout > TestEssentials.connection_timeout

    # Act
    act(xift)

    # Assert parameters
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [(TestEssentials.control_topic_name, 1)], 0),
                              call.broker.on_client_disconnect(ANY, ANY, 1) ]
    #expected_calls_client = [ call.client.on_connect_finish(XiClientErrorCodes.CONTROL_TOPIC_SUBSCRIPTION_ERROR)]
    expected_calls_client = [ call.client.on_connect_finish(XiClientErrorCodes.SUCCESS)]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_connect_controlTopicSubscriptionRefused_conClbCalledWithSuccess(xift):
    """
        Tests the behaviour of the client when the broker responds to control topic
        subscription with an error code

        Test scenario:
            Make the server to receive the CONNECT msg from the client
            send the CONNACK response and send invalid SUBACK response

        Expectations:
            Client should invoke connection finished callback with SUCCESS
    """

    xift.client_sut.on_connect_finish.side_effect = lambda connect_res: xift.client_sut.disconnect()
    xift.client_sut.on_disconnect.side_effect = lambda return_code: xift.client_sut.stop()


    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
            xift.broker.send_connack( mqtt_messages.CONNACK_ACCEPTED )
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
            xift.broker.send_suback(msg_id, [(TestEssentials.control_topic_name, 0x80)])
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: \
            xift.broker.trigger_shutdown()

    # Set the connection timeout based on the actual test value
    TestEssentials.connection_timeout = 2

    # Sanity checks
    assert TestEssentials.connection_timeout > 0
    assert TestEssentials.test_timeout > TestEssentials.connection_timeout

    # Act
    act(xift)

    # Assert parameters
    expected_calls_broker = [  call.broker.on_client_connect(ANY, ANY),
                               call.broker.on_client_subscribe(ANY, ANY,
                                [(TestEssentials.control_topic_name, 1)], 0),
                               call.broker.on_client_disconnect(ANY, ANY, 0) ]
    expected_calls_client = [ call.client.on_connect_finish(XiClientErrorCodes.SUCCESS),
                              call.client.on_disconnect(0) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_visualization_test_not_needed_for_some_platforms(xift):
    if (xift.sut_platform == XiClientPlatform.PYTHON_2 or
        xift.sut_platform == XiClientPlatform.PYTHON_3):
        pytest.xfail("test excluded for some platforms")

def test_visualization_test_not_implemented_test_case(xift):
    pytest.skip("not implemented")

