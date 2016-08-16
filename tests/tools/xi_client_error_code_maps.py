from tools.xi_client_error_codes import XiClientErrorCodes

def xi_client_error_code_map_c( error_code ):
    # xi_err.h error code mapping
    if error_code is 1:
        return XiClientErrorCodes.TIMEOUT
    elif error_code is 17:
        return XiClientErrorCodes.CONNECTION_RESET_BY_PEER
    elif error_code is 20 or \
         error_code is 62:
        return XiClientErrorCodes.CERTERROR
    elif error_code is 21: # XI_TLS_CONNECT_ERROR
        return XiClientErrorCodes.SSLERROR
    elif error_code is 30:
        return XiClientErrorCodes.MQTT_PROTOCOL_VERSION
    elif error_code is 32:
        return XiClientErrorCodes.MQTT_SERVER_UNAVAILABLE
    elif error_code is 31:
        return XiClientErrorCodes.MQTT_IDENTIFIER_REJECTED
    elif error_code is 33:
        return XiClientErrorCodes.MQTT_BAD_USERNAME_OR_PASSWORD
    elif error_code is 34:
        return XiClientErrorCodes.MQTT_NOT_AUTHORISED
    return error_code


import os
import sys
sys.path.insert( 1, os.getcwd() + "/../../../xi_client_py/src/" )
from xiPy.xively_error_codes import XivelyErrorCodes as xec

def xi_client_error_code_map_py( error_code ):
    xec_to_conn_response = {
          xec.XI_TLS_CONNECT_ERROR : XiClientErrorCodes.SSLERROR
        , xec.XI_TLS_CERTIFICATE_ERROR : XiClientErrorCodes.CERTERROR
        , xec.XI_STATE_OK : XiClientErrorCodes.SUCCESS
        , xec.XI_STATE_TIMEOUT : XiClientErrorCodes.TIMEOUT
        , xec.XI_MQTT_IDENTIFIER_REJECTED : XiClientErrorCodes.MQTT_IDENTIFIER_REJECTED
        , xec.XI_MQTT_NOT_AUTHORIZED : XiClientErrorCodes.MQTT_NOT_AUTHORISED
        , xec.XI_MQTT_SERVER_UNAVAILIBLE : XiClientErrorCodes.MQTT_SERVER_UNAVAILABLE
        , xec.XI_MQTT_UNACCEPTABLE_PROTOCOL_VERSION : XiClientErrorCodes.MQTT_PROTOCOL_VERSION
        , xec.XI_MQTT_BAD_USERNAME_OR_PASSWORD : XiClientErrorCodes.MQTT_BAD_USERNAME_OR_PASSWORD
        , xec.XI_SOCKET_ERROR : XiClientErrorCodes.SOCKET_ERROR
        , xec.XI_CONTROL_TOPIC_SUBSCRIPTION_ERROR : XiClientErrorCodes.CONTROL_TOPIC_SUBSCRIPTION_ERROR
        , xec.XI_CONNECTION_RESET_BY_PEER_ERROR : XiClientErrorCodes.CONNECTION_RESET_BY_PEER
    }
    return xec_to_conn_response[error_code]
