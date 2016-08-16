from tools.xi_ftest_fixture import xift
from tools.xi_ftest_fixture import sut_platform
from tools.xi_ftest_fixture import act

from tools.xi_client_error_codes import XiClientErrorCodes

from unittest.mock import ANY, call
from tools.xi_mock_broker import mqtt_messages
from tools.xi_utils import BasicMessageMatcher
from tools.xi_ftest_fixture import TestEssentials

import xi_ftest_clean_session_helpers as helpers

# test scenarios:
# - all scenarios need at least one reconnection
# - connections with clean session flag:
#       2 connections:
#       - OFF - OFF
#       - OFF - ON
#       - ON  - OFF
#       - ON  - ON
#       3 connections:
#       - OFF - OFF - OFF
#       - OFF - OFF - ON
#       - OFF - ON  - OFF
#       - OFF - ON  - ON
#       - ON  - OFF - OFF
#       - ON  - OFF - ON
#       - ON  - ON  - OFF
#       - ON  - ON  - ON

# - use a single PUBLISH to check proper client clean session behaviour
# - use multiple PUBLISHes to check proper client clean session behaviour
#       - none of the PUBLISHes get ACKed before disconnect
#       - only some of PUBLISHes are ACKed before disconnect

# - same as the latter but with SUBSCRIBE / SUBSCRIBEs

# - "negative" tests: all PUBLISHes, SUBSCRIBEs got ACKed, so upon reconnect
#   no retransmission is needed

def test_clean_session_PUB__2_UNCLEAN_UNCLEAN_broker_disconnect__client_redelivers_PUBLISH(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue          = [ 0, 0 ]
    client_on_connect_action_queue    = [ 1, 0 ]
    broker_on_message_action_queue    = [ 3, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0', 1 )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.CONNECTION_RESET_BY_PEER),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_publish_finish(ANY),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS)]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_PUB__2_UNCLEAN_UNCLEAN__client_redelivers_PUBLISH(xift):

    clean_session_flag_queue          = [ 0, 0 ]
    client_on_connect_action_queue    = [ 1, 0 ]
    broker_on_message_action_queue    = [ 2, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0', 1 )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_publish_finish(ANY),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_PUB__2_UNCLEAN_UNCLEAN__client_redelivers_PUBLISH_and_sends_new_PUBLISH(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue          = [ 0, 0 ]
    client_on_connect_action_queue    = [ 1, 1 ]
    broker_on_message_action_queue    = [ 2, 1, 1 ]
    client_on_publish_action_queue    = [ 0, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue,
        client_on_publish_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0', 1 )),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm1', 0 )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY)]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_publish_finish(ANY),
                              call.client.on_publish_finish(ANY),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_PUB__2_UNCLEAN_UNCLEAN_2_PUBs__client_redelivers_PUBLISHes(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue                = [ 0,    0    ]
    client_on_connect_action_queue          = [ 2,    0    ]
    broker_on_message_action_queue          = [ 0, 2, 1, 1 ]
    client_on_publish_finish_action_queue   = [       0, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue,
        client_on_publish_finish_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0#1' )),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0#2' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0#1', 1 )),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0#2', 1 )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_publish_finish(ANY),
                              call.client.on_publish_finish(ANY),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_PUB__2_UNCLEAN_CLEAN__NO_redelivery(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue          = [ 0, 1 ]
    client_on_connect_action_queue    = [ 1, 9 ]
    broker_on_message_action_queue    = [ 2, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_PUB__2_CLEAN_UNCLEAN__NO_redelivery(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue          = [ 1, 0 ]
    client_on_connect_action_queue    = [ 1, 9 ]
    broker_on_message_action_queue    = [ 2, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_PUB__2_CLEAN_CLEAN__NO_redelivery(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue          = [ 1, 1 ]
    client_on_connect_action_queue    = [ 1, 9 ]
    broker_on_message_action_queue    = [ 2, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls


############# 3 sessions ###################################

def test_clean_session_PUB__3_UNCLEAN_UNCLEAN_UNCLEAN__redeliver_on_2nd_but_NO_redelivery_on_3rd(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue          = [ 0, 0, 0 ]
    client_on_connect_action_queue    = [ 1, 0, 9 ]
    broker_on_message_action_queue    = [ 2, 1, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0', 1 )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_publish_finish(ANY),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_PUB__3_UNCLEAN_UNCLEAN_UNCLEAN__redelivery_on_3rd(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue          = [ 0, 0, 0 ]
    client_on_connect_action_queue    = [ 1, 0, 0 ]
    broker_on_message_action_queue    = [ 2, 2, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0', 1 )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0', 1 )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_publish_finish(ANY),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_PUB__3_UNCLEAN_UNCLEAN_UNCLEAN_2_PUBs__redelivery_on_3rd(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue                = [ 0,    0,    0    ]
    client_on_connect_action_queue          = [ 2,    0,    0    ]
    broker_on_message_action_queue          = [ 0, 2, 0, 2, 1, 1 ]
    client_on_publish_finish_action_queue   = [             0, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue,
        client_on_publish_finish_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0#1' )),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0#2' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0#1', 1 )),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0#2', 1 )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0#1', 1 )),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0#2', 1 )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_publish_finish(ANY),
                              call.client.on_publish_finish(ANY),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_PUB__3_UNCLEAN_CLEAN_UNCLEAN__NO_redelivery(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue          = [ 0, 1, 0 ]
    client_on_connect_action_queue    = [ 1, 9, 9 ]
    broker_on_message_action_queue    = [ 2, 1, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_PUB__3_UNCLEAN_UNCLEAN_UNCLEAN_happy_broker__NO_redelivery(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue          = [ 0, 0, 0 ]
    client_on_connect_action_queue    = [ 1, 1, 9 ]
    broker_on_message_action_queue    = [ 1, 1, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        broker_on_message_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm0' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_message(ANY, ANY,
                                BasicMessageMatcher(TestEssentials.topic, 1, b'tm1' )),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_publish_finish(ANY),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_publish_finish(ANY),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls
