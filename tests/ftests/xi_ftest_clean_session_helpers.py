from tools.xi_utils import Counter
from tools.xi_mock_broker import mqtt_messages
from tools.xi_ftest_fixture import TestEssentials
import time

################### client custom actions ################################################
def generator_client_connect( xift, clean_session_flag_queue ):
    counter = Counter()

    client_connect_original = xift.client_sut.connect

    def client_connect_wrapper( a, connect_options, c ):
        #print("================ client_connect_wrapper")

        if 0 == clean_session_flag_queue[ counter.get() ]:
            connect_options.connect_flags &= ~mqtt_messages.CLEAN_SESSION_FLAG
        else:
            connect_options.connect_flags |=  mqtt_messages.CLEAN_SESSION_FLAG

        client_connect_original( a, connect_options, c )

        counter.inc()

    return client_connect_wrapper

def generator_client_on_connect_finish( xift, client_on_connect_action_queue ):
    counter = Counter()

    def client_on_connect_finish( result ):
        print("================== client_on_connect_finish")
        if 0 == client_on_connect_action_queue[ counter.get() ]:
            # no-operation
            pass
        elif 1 == client_on_connect_action_queue[ counter.get() ]:
            print("================== client_on_connect_finish, PUBLISHing")
            xift.client_sut.publish_string(TestEssentials.topic,
                "tm" + str(counter.get()), 1 )
        elif 2 == client_on_connect_action_queue[ counter.get() ]:
            print("================== client_on_connect_finish, 2x PUBLISHing")
            xift.client_sut.publish_string(TestEssentials.topic,
                "tm" + str(counter.get()) + "#1", 1 )
            time.sleep( 0.1 )
            xift.client_sut.publish_string(TestEssentials.topic,
                "tm" + str(counter.get()) + "#2", 1 )
        elif 11 == client_on_connect_action_queue[ counter.get() ]:
            print("================== client_on_connect_finish, SUBSCRIBEing")
            xift.client_sut.subscribe( [ [ TestEssentials.topic, 0 ] ] )
        elif 12 == client_on_connect_action_queue[ counter.get() ]:
            print("================== client_on_connect_finish, 2x SUBSCRIBEing")
            xift.client_sut.subscribe( [ [ TestEssentials.topic, 0 ] ] )
            time.sleep( 0.1 )
            xift.client_sut.subscribe( [ [ TestEssentials.topic, 1 ] ] )
        elif 21 == client_on_connect_action_queue[ counter.get() ]:
            xift.client_sut.publish_string(TestEssentials.topic,
                "tm" + str(counter.get()), 1 )
            time.sleep( 0.1 )
            xift.client_sut.subscribe( [ [ TestEssentials.topic, 0 ] ] )
        elif 22 == client_on_connect_action_queue[ counter.get() ]:
            xift.client_sut.subscribe( [ [ TestEssentials.topic, 0 ] ] )
            time.sleep( 0.1 )
            xift.client_sut.publish_string(TestEssentials.topic,
                "tm" + str(counter.get()), 1 )
        elif 9 == client_on_connect_action_queue[ counter.get() ]:
            #time.sleep(0.5)
            xift.client_sut.disconnect()

        counter.inc()

    return client_on_connect_finish

def generator_client_on_publish_finish( xift, client_on_publish_action_queue ):
    counter = Counter()

    def client_on_publish_finish( result ):

        if len(client_on_publish_action_queue) <= counter.get() or \
            0 != client_on_publish_action_queue[ counter.get() ]:

            print("========================================= disconnecting client from on_publish_finish")
            xift.client_sut.disconnect()

        counter.inc()

    return client_on_publish_finish

def generator_client_on_subscribe_finish( xift, client_on_subscribe_finish_action_queue ):
    counter = Counter()

    def client_on_subscribe_finish( result_queue ):

        if len(client_on_subscribe_finish_action_queue) <= counter.get() or \
            0 != client_on_subscribe_finish_action_queue[ counter.get() ]:

            print("========================================= disconnecting client from on_subscribe_finish coutner = %d" % counter.get() )
            xift.client_sut.disconnect()

        counter.inc()

    return client_on_subscribe_finish

def generator_client_on_disconnect( xift, number_of_reconnections ):
    counter = Counter()

    def client_on_disconnect( disconnect_reason ):

        if counter.get() < number_of_reconnections:
            xift.client_sut.connect(xift.broker.bind_address,
                                    xift.connect_options,
                                    TestEssentials.connection_timeout)
        else:
            xift.client_sut.stop()

        counter.inc()

    return client_on_disconnect



################### broker custom actions ################################################
def generator_broker_on_client_disconnect( xift, shut_down_at ):
    counter = Counter()

    print("================== shut down at: " + str(shut_down_at))

    def broker_on_client_disconnect( br, user_data, disconnect_reason ):
        print("================== client disconnected from BROKER")
        if counter.is_at( shut_down_at ):
            print("================== shutting down the BROKER")
            xift.broker.trigger_shutdown()
        else:
            print("================== keeping BROKER up and running for now")

        counter.inc()

    return broker_on_client_disconnect

def generator_broker_on_message( xift, broker_on_message_action_queue ):
    counter = Counter()

    def broker_on_message( a, b, mqtt_message ):
        print("================== message from client at BROKER")

        try:

            if 0 == broker_on_message_action_queue[ counter.get() ]:
                # no-operation
                pass
            elif 1 == broker_on_message_action_queue[ counter.get() ]:
                print("================== sending PUBACK")
                xift.broker.send_puback(mqtt_message.mid)

            elif 2 == broker_on_message_action_queue[ counter.get() ]:
                print("================== disconnecting the client from generator_broker_on_message")
                xift.client_sut.disconnect()

            elif 3 == broker_on_message_action_queue[ counter.get() ]:
                print("================== disconnecting the broker from generator_broker_on_message")
                # this will result in backoff level increase on client side,
                # next client connection will take longer
                xift.broker.disconnect()

            counter.inc()
        except:
            print( "=============== exception in generator_broker_on_message counter = %d" % counter.get() )

    return broker_on_message

def generator_broker_on_subscribe( xift, broker_on_subscribe_action_queue ):
    counter = Counter()

    def broker_on_subscribe( user_data, msg_id, topics_and_qos, dup ):
        print("================== subscription from client at BROKER: " +
            str( topics_and_qos ) )

        if  0 == len( broker_on_subscribe_action_queue ) or \
            1 == broker_on_subscribe_action_queue[ counter.get() ]:
            print("================== sending SUBACK")
            xift.broker.send_suback( msg_id, topics_and_qos )

        elif 0 == broker_on_subscribe_action_queue[ counter.get() ]:
            # no-operation
            pass
        elif 2 == broker_on_subscribe_action_queue[ counter.get() ]:
            print("================== disconnecting the client")
            xift.client_sut.disconnect()

        elif 3 == broker_on_subscribe_action_queue[ counter.get() ]:
            print("================== disconnecting the broker")
            # this will result in backoff level increase on client side,
            # next client connection will take longer
            xift.broker.disconnect()

        counter.inc()

    return broker_on_subscribe

################### test case custom setup ###############################################
def generator_test_case_setup( xift,
                               clean_session_flag_queue,
                               client_on_connect_action_queue,
                               broker_on_message_action_queue,
                               client_on_publish_action_queue = [],
                               broker_on_subscribe_action_queue = [],
                               client_on_subscribe_finish_action_queue = [] ):

    # grep output on '###' will return all clean session test configs
    print("#######################################")
    print("### clean_session_flag_queue                 : " +
        str(clean_session_flag_queue))
    print("### client_on_connect_action_queue           : " +
        str(client_on_connect_action_queue))
    print("### broker_on_message_action_queue           : " +
        str(broker_on_message_action_queue))
    print("### client_on_publish_action_queue           : " +
        str(client_on_publish_action_queue))
    print("### broker_on_subscribe_action_queue         : " +
        str(broker_on_subscribe_action_queue))
    print("### client_on_subscribe_finish_action_queue  : " +
        str(client_on_subscribe_finish_action_queue))


    number_of_reconnections = len(client_on_connect_action_queue) - 1

    ##### broker behaviour ####################################
    xift.broker.on_client_connect.side_effect = lambda userdata, connect_options: \
                        xift.broker.send_connack(mqtt_messages.CONNACK_ACCEPTED)

    xift.broker.on_message.side_effect = \
        generator_broker_on_message( xift, broker_on_message_action_queue )

    xift.broker.on_client_subscribe.side_effect = lambda userdata, msg_id, topics_and_qos, dup: \
                        xift.broker.send_suback(msg_id, topics_and_qos)

    xift.broker.on_client_subscribe.side_effect = \
        generator_broker_on_subscribe( xift, broker_on_subscribe_action_queue )

    xift.broker.on_client_disconnect.side_effect = \
        generator_broker_on_client_disconnect( xift, number_of_reconnections )

    ##### client behaviour #####################################
    xift.client_sut.on_connect_finish.side_effect = \
        generator_client_on_connect_finish( xift, client_on_connect_action_queue )

    xift.client_sut.on_publish_finish.side_effect = \
        generator_client_on_publish_finish( xift, client_on_publish_action_queue )

    xift.client_sut.on_subscribe_finish.side_effect = \
        generator_client_on_subscribe_finish( xift, client_on_subscribe_finish_action_queue )

    xift.client_sut.on_disconnect.side_effect = \
        generator_client_on_disconnect( xift, number_of_reconnections )

    ##### client behaviour, override connect ###################
    xift.client_sut.connect = \
        generator_client_connect( xift, clean_session_flag_queue )
