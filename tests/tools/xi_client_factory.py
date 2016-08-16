
import tools.xi_client_runner_javascript as xi_client_runner_js
import tools.xi_client_runner as xi_client_runner

import tools.xi_client_error_code_maps as error_code_maps
from tools.xi_client_error_codes import XiClientErrorCodes
from tools.xi_client_settings import XiClientPlatform
from tools.xi_client_settings import XiClientSocketType

import tools.xi_client_driver_starters as xi_client_driver_starters
from tools.xi_control_channel_codec_protobuf_runner import XiControlChannel_codec_protobuf_runner
from tools.xi_control_channel_transp_socket import XiControlChannel_transp_socket
import tools.xi_client_settings

import os
import sys
sys.path.insert( 1, os.getcwd() + "/../../../xi_client_py/src/" )
from xiPy.xively_error_codes import XivelyErrorCodes as xec

class XiClientFactory:
    @staticmethod
    def __instantiate_xi_client_runner(function_error_code_map, driver_starter, is_transport_socket):
        control_channel_codec = XiControlChannel_codec_protobuf_runner(function_error_code_map)
        control_channel_transport = XiControlChannel_transp_socket(control_channel_codec)

        client_runner = xi_client_runner.XiClientRunner(
            driver_starter,
            control_channel_codec,
            control_channel_transport)

        ######################################################################
        # wiring up components to each other
        control_channel_codec.xi_callback_sink = client_runner
        control_channel_codec.control_channel = control_channel_transport

        return client_runner

    @staticmethod
    def generate_xi_client(platform,socket_type):

        if platform == XiClientPlatform.JAVASCRIPT:
            return xi_client_runner_js.XiClientRunnerJavascriptPaho()

        elif platform == XiClientPlatform.C:

            return XiClientFactory.__instantiate_xi_client_runner(
                error_code_maps.xi_client_error_code_map_c,
                xi_client_driver_starters.XiClientDriverStarter_C(),
                True)

        elif (platform == XiClientPlatform.PYTHON_2 or
              platform == XiClientPlatform.PYTHON_3):

            return XiClientFactory.__instantiate_xi_client_runner(
                error_code_maps.xi_client_error_code_map_py,
                xi_client_driver_starters.XiClientDriverStarter_py(platform, socket_type == XiClientSocketType.WEBSOCKET),
                True)

        # default to paho python
        return XiClientFactory.__instantiate_xi_client_runner(
            error_code_maps.xi_client_error_code_map_py,
            xi_client_driver_starters.XiClientDriverStarter_py(XiClientPlatform.PYTHON_3,
                                                               socket_type == XiClientSocketType.WEBSOCKET),
            True)

#                                             |
#          RUNNER                             |                          DRIVER
#                                      process|border
#       ------------------                    |
#     /                   |                   |
# client <-> codec <-> transport  <=====communication======> transport <-> codec <-> "real" client
#    |                                        |
#    V                                        |
# starter
