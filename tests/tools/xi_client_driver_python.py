import os
import sys, getopt

from xi_control_channel_codec_protobuf_driver import XiControlChannel_codec_protobuf_driver
from xi_control_channel_transp_socket import XiControlChannel_transp_socket

sys.path.insert( 1, os.getcwd() + "/../../../xi_client_py/src/" )
from xiPy.xively_client import XivelyClient
from xiPy.xively_client import XivelyConfig
from xiPy.xively_connection_parameters import XivelyConnectionParameters

def __xi_driver_init(argv):
    #print('Number of arguments:', len(argv), 'arguments.')
    #print('Argument List:', str(argv))

    try:
        opts, args = getopt.getopt(argv[1:],"h:p:w")
    except getopt.GetoptError:
        print('error during command line parsing')
        sys.exit(2)

    is_websocket = False

    for opt, arg in opts:
        if opt == '-h':
            #print("host = " + arg)
            host = arg
        elif opt == '-p':
            #print("port = " + str(arg))
            port = arg
        elif opt == '-w':
            #print("websocket")
            is_websocket = True

    return host, port, is_websocket


if __name__ == '__main__':

    cc_host, cc_port, xi_is_websocket = __xi_driver_init(sys.argv)

    # transport <--> codec <--> xi_client

    xi_client_connection_params = XivelyConnectionParameters()
    xi_client_connection_params.clean_session = True
    xi_client_connection_params.use_websocket = xi_is_websocket

    xi_client = XivelyClient()

    control_channel_codec = XiControlChannel_codec_protobuf_driver(xi_client, xi_client_connection_params)
    control_channel_transport = XiControlChannel_transp_socket(control_channel_codec)

    xi_client.on_connect_finished = control_channel_codec.on_connect_finish
    xi_client.on_disconnect_finished = control_channel_codec.on_disconnect_finish
    xi_client.on_subscribe_finished = control_channel_codec.on_subscribe_finish
    xi_client.on_message_received = control_channel_codec.on_message_received
    xi_client.on_publish_finished = control_channel_codec.on_publish_finish

    control_channel_codec.control_channel = control_channel_transport

    control_channel_transport.connect(cc_host, int(cc_port))
