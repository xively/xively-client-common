import pytest
from tools.xi_ftest_fixture import xift
from tools.xi_ftest_fixture import sut_platform
from tools.xi_ftest_fixture import TestEssentials
from tools.xi_ftest_fixture import act


from unittest.mock import ANY, call
from tools.xi_utils import Counter
from tools.xi_mock_broker import mqtt_messages
from tools.xi_mock_broker.mqtt_messages import MQTT_ERR_SUCCESS, MQTT_ERR_CONN_LOST
import threading

def off_test_ftest_lecture_threading_1(xift):



    broker_flow =  [ call.broker.on_client_connect(ANY, ANY),
                      call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                      call.broker.on_client_subscribe(ANY, ANY, ANY, 0),
                      call.broker.on_client_disconnect(xift.broker, ANY, MQTT_ERR_SUCCESS)]

    def broker_on_client_connect(userdata, connect_options):
        print("*** [ broker ] [ " + threading.current_thread().getName() + " ] broker_on_client_connect")
        xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    xift.broker.on_client_connect.side_effect = broker_on_client_connect

    def broker_on_client_subscribe(userdata, msg_id, topics_and_qos):
        print("*** [ broker ] [ " + threading.current_thread().getName() + " ] broker_on_client_subscribe")
        xift.broker.send_suback( msg_id, topics_and_qos )

    xift.broker.on_client_subscribe.side_effect = broker_on_client_subscribe

    def broker_on_client_disconnect(br, userdata, rc):
        print("*** [ broker ] [ " + threading.current_thread().getName() + " ] broker_on_client_disconnect")
        xift.broker.trigger_shutdown()

    xift.broker.on_client_disconnect.side_effect = broker_on_client_disconnect



    xift.client_sut._exception_queue = xift._task_queue

    def client_on_connect_finish(connect_res):
        print("*** [ client ] [ " + threading.current_thread().getName() + " ] client_on_connect_finish")
        xift.client_sut.subscribe([[TestEssentials.topic, 1]])

    xift.client_sut.on_connect_finish.side_effect = client_on_connect_finish

    def client_on_subscribe_finish(granted_access_list):
        print("*** [ client ] [ " + threading.current_thread().getName() + " ] client_on_subscribe_finish")
        xift.client_sut.disconnect()

    xift.client_sut.on_subscribe_finish.side_effect = client_on_subscribe_finish

    def client_on_disconnect(return_code):
        print("*** [ client ] [ " + threading.current_thread().getName() + " ] client_on_disconnect")
        xift.client_sut.stop()

        def assert_on_return_code():
            assert return_code == 1

        xift._task_queue.put(assert_on_return_code)


    xift.client_sut.on_disconnect.side_effect = client_on_disconnect




    ###
    # Act
    print("\n")
    print("*** [ act    ] [ " + threading.current_thread().getName() + " ] act")
    act(xift)



    client_flow = [ call.client.on_connect_finish(mqtt_messages.CONNACK_ACCEPTED),
                    call.client.on_subscribe_finish(ANY),
                    call.client.on_disconnect(0)]

    ###
    # Assert
    print("*** [ assert ] [ " + threading.current_thread().getName() + " ] asserting on main thread")
    assert broker_flow == xift.mock_call_history_broker.method_calls
    assert client_flow == xift.mock_call_history_client.method_calls
