import pytest
from tools.xi_ftest_fixture import xift
from tools.xi_ftest_fixture import sut_platform
from tools.xi_ftest_fixture import TestEssentials
from tools.xi_ftest_fixture import act

from unittest.mock import ANY, call
from tools.xi_utils import Counter
from tools.xi_mock_broker import mqtt_messages
from tools.xi_mock_broker.mqtt_messages import MQTT_ERR_SUCCESS

def connect_common(xift, username, password, connect_flags_expected):
    # Arrange
    xift.connect_options.username = username
    xift.connect_options.password = password

    xift.client_sut.on_connect_finish.side_effect = lambda connect_res: xift.client_sut.disconnect()
    xift.client_sut.on_disconnect.side_effect = lambda return_code: xift.client_sut.stop()

    def validate_connection(userdata, connect_options):

        # 128   USERNAME_FLAG = 0x80
        # 64    PASSWORD_FLAG = 0x40
        # 32    WILL_RETAIN_FLAG = 0x20
        # 24    WILL_QOS_FLAG = 0x18
        # 4     WILL_FLAG = 0x04
        # 2     CLEAN_SESSION_FLAG = 0x02
        def assert_connect_options():
            assert connect_options.connect_flags == connect_flags_expected
            assert username == xift.connect_options.username
            assert password == xift.connect_options.password

        xift._task_queue.put(assert_connect_options)

        xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    xift.broker.on_client_connect.side_effect = validate_connection
    xift.broker.on_client_disconnect.side_effect = lambda br, userdata, rc: \
        xift.broker.trigger_shutdown()
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
        xift.broker.send_suback(msg_id, topics_and_qos)

    # Act
    act(xift)

    # Assert
    expected_calls_broker = [ call.broker.on_client_connect(ANY, ANY) ]
    expected_calls_client = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED) ]
    xift.mock_call_history_broker.assert_has_calls(expected_calls_broker)
    xift.mock_call_history_client.assert_has_calls(expected_calls_client)

    assert expected_calls_broker == xift.mock_call_history_broker.method_calls[:1]
    assert expected_calls_client == xift.mock_call_history_client.method_calls[:1]

def test_authentication_nonEmptyUsername_nonEmptyPassword_usernameAndPasswordFlagsMustBeSet(xift):
    connect_common(xift, "This is a valid username &^&%$%#@", "This is a valid password &^&%$%#@",
        mqtt_messages.USERNAME_FLAG | mqtt_messages.PASSWORD_FLAG)

def test_authentication_nonEmptyUsername_emptyPassword_usernameAndPasswordFlagsMustBeSet(xift):
    connect_common(xift, "auth_test_username", "",
        mqtt_messages.USERNAME_FLAG | mqtt_messages.PASSWORD_FLAG)

def test_authentication_emptyUsername_nonEmptyPassword_usernameAndPasswordFlagsMustBeSet(xift):
    connect_common(xift, "", "auth_test_password", mqtt_messages.USERNAME_FLAG | mqtt_messages.PASSWORD_FLAG)

def test_authentication_emptyUsername_emptyPassword_usernameAndPasswordFlagsMustBeSet(xift):
    connect_common(xift, "", "", mqtt_messages.USERNAME_FLAG | mqtt_messages.PASSWORD_FLAG)

@pytest.mark.xfail( reason = "This test require mock broker to be able to pass None if the username and password is not set during the connection." )
def test_authentication_usernameNotSet_passwordNotSet_usernameAndPasswordFlagsMustNotBeSet(xift):
    connect_common(xift, None, None, 0)
