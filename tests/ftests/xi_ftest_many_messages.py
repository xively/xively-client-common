import pytest

from tools.xi_ftest_fixture import xift
from tools.xi_ftest_fixture import sut_platform
from tools.xi_ftest_fixture import TestEssentials
from tools.xi_ftest_fixture import act

from unittest.mock import ANY, call
from tools.xi_utils import Counter, BasicMessageMatcher
from tools.xi_mock_broker import mqtt_messages
from tools.xi_client_error_codes import XiClientErrorCodes

import random

# globals
payload_seed = [ chr( c ) for c in range(92, 122) ]
messages_to_receive = 0

class mqtt_publish_parameters:
    """
    Helper class that encapsulates publish test parameters
    """
    def __init__(self, mqtt_msg_payload_size_min_max, mqtt_msg_count):
        self.mqtt_msg_payload_size_min_max = mqtt_msg_payload_size_min_max
        self.mqtt_msg_count = mqtt_msg_count

"""
Generates the test parameters so that we can use same test implementation with different settings
"""
@pytest.fixture(scope="function"
                ,params=[ mqtt_publish_parameters((1,15), 10)
                         , mqtt_publish_parameters((1,15), 20)
                         , mqtt_publish_parameters((1,15), 25)
                         , mqtt_publish_parameters((5,25), 50)]
                ,ids=[ "PUBLISH_10_MSGS_MSG_LEN(1,15)"
                      , "PUBLISH_20_MSGS_MSG_LEN(1,15)"
                      , "PUBLISH_25_MSGS_MSG_LEN(1,15)"
                      , "PUBLISH_50_MSGS_MSG_LEN(5,25)"])
def publish_parameters_setup(request):
    return request.param

def gen_message_payload(msg_len_min_max):
    """
    Generates random and human readable msg payload within the range between min_len and max_len
    """
    min_len, max_len = msg_len_min_max
    msg_len = random.randint(min_len,max_len)
    return "".join([random.choice(payload_seed) for i in range(0,msg_len)])

def test_publish_many_messages_in_one_buffer(xift, publish_parameters_setup ):
    """
        Tests if the client is capable of receiving several messages glued together
        so that the receive buffer may contain some pending data prereserved.
    """

    global messages_to_receive

    messages_to_send = publish_parameters_setup.mqtt_msg_count
    messages_to_receive = messages_to_send

    messages_received = []

    def on_subscribe_finish( result_queue ):
        for i in range(0, messages_to_send):
            xift.broker.publish(TestEssentials.topic
                , gen_message_payload(publish_parameters_setup.mqtt_msg_payload_size_min_max))

    def on_message_received( topic, message ):
        global messages_to_receive
        messages_to_receive  -= 1
        messages_received.append( call.client.on_message_received( TestEssentials.topic, message ) )
        if messages_to_receive == 0:
            xift.client_sut.disconnect()

    def on_disconnect( result ):
        xift.client_sut.stop()

    # 1. accept the connection
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
        xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    # 2. accept the control topic submission
    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
        xift.broker.send_suback(msg_id, topics_and_qos)

    #  3. on connect response, subscribe to topic
    xift.client_sut.on_connect_finish.side_effect = lambda connect_response: \
        xift.client_sut.subscribe( [ [ TestEssentials.topic, 0 ] ] )

    xift.client_sut.on_disconnect = on_disconnect
    xift.client_sut.on_subscribe_finish.side_effect = on_subscribe_finish
    xift.client_sut.on_message_received.side_effect = on_message_received

    xift.client_sut.on_publish_finish.side_effect = None
    xift.broker.on_client_disconnect.side_effect = lambda value: \
        xift.broker.trigger_shutdown()

    ####
    # Act
    act(xift)

    expected_calls_broker = [ call.broker.on_client_connect(ANY,ANY)
                            , call.broker.on_client_subscribe(ANY, ANY, ANY, 0)
                            , call.broker.on_client_subscribe(ANY, ANY, ANY, 0)
                            , call.broker.on_client_disconnect(ANY, ANY, 0) ]

    expected_calls_client = [ call.client.on_connect_finish(XiClientErrorCodes.SUCCESS)
                            , call.client.on_subscribe_finish(ANY)]

    expected_calls_client += messages_received

    assert xift.mock_call_history_broker.method_calls == expected_calls_broker
    assert xift.mock_call_history_client.method_calls == expected_calls_client


