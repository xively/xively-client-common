from tools.xi_ftest_fixture import xift
from tools.xi_ftest_fixture import sut_platform
from tools.xi_ftest_fixture import act

from tools.xi_client_error_codes import XiClientErrorCodes

from unittest.mock import ANY, call
from tools.xi_mock_broker import mqtt_messages
from tools.xi_utils import BasicMessageMatcher
from tools.xi_ftest_fixture import TestEssentials

import xi_ftest_clean_session_helpers as helpers

def test_clean_session_SUB__2_UNCLEAN_UNCLEAN__client_reSUBSCRIBES(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue            = [   0,      0     ]
    client_on_connect_action_queue      = [  11,      0     ]
    broker_on_subscribe_action_queue    = [   1,  2,  1,  1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        [],
        [],
        broker_on_subscribe_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [ ( TestEssentials.topic_as_bytes, 0 ) ], 0 ),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [ ( TestEssentials.topic_as_bytes, 0 ) ], 1 ),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_subscribe_finish( [ XiClientErrorCodes.SUCCESS ] ),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_SUB__2_UNCLEAN_UNCLEAN_2SUBs_client_reSUBSCRIBES(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue                = [  0,          0         ]
    client_on_connect_action_queue          = [ 12,          0         ]
    broker_on_subscribe_action_queue        = [  1,  0,  2,  1,  1,  1 ]
    client_on_subscribe_finish_action_queue = [                  0,  1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        [],
        [],
        broker_on_subscribe_action_queue,
        client_on_subscribe_finish_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [ ( TestEssentials.topic_as_bytes, 0 ) ], 0 ),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [ ( TestEssentials.topic_as_bytes, 1 ) ], 0 ),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [ ( TestEssentials.topic_as_bytes, 0 ) ], 1 ),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [ ( TestEssentials.topic_as_bytes, 1 ) ], 1 ),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_subscribe_finish( [ 0 ] ),
                              call.client.on_subscribe_finish( [ 1 ] ),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls


def test_clean_session_SUB__3_UNCLEAN_UNCLEAN_UNCLEAN__client_reSUBSCRIBES(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue            = [   0,      0,      0     ]
    client_on_connect_action_queue      = [  11,      0,      0     ]
    broker_on_subscribe_action_queue    = [   1,  2,  1,  2,  1,  1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        [],
        [],
        broker_on_subscribe_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [ ( TestEssentials.topic_as_bytes, 0 ) ], 0 ),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [ ( TestEssentials.topic_as_bytes, 0 ) ], 1 ),
                              call.broker.on_client_disconnect(ANY, ANY, ANY),
                              call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [ ( TestEssentials.topic_as_bytes, 0 ) ], 1 ),
                              call.broker.on_client_disconnect(ANY, ANY, ANY) ]

    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS),
                              call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                              call.client.on_subscribe_finish( [ XiClientErrorCodes.SUCCESS ] ),
                              call.client.on_disconnect(XiClientErrorCodes.SUCCESS) ]

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls
    assert expected_calls_client == xift.mock_call_history_client.method_calls

def test_clean_session_SUB__3_UNCLEAN_CLEAN_UNCLEAN__client_NO_redelivery(xift):

    ''' see xi_ftest_clean_session_helpers.py for the matrix codes below '''
    clean_session_flag_queue            = [   0,      1, 0 ]
    client_on_connect_action_queue      = [  11,      9, 9 ]
    broker_on_subscribe_action_queue    = [   1,  2,  1, 1 ]

    helpers.generator_test_case_setup( xift,
        clean_session_flag_queue,
        client_on_connect_action_queue,
        [],
        [],
        broker_on_subscribe_action_queue )

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY),
                              call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                              call.broker.on_client_subscribe(ANY, ANY,
                                [ ( TestEssentials.topic_as_bytes, 0 ) ], 0 ),
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
