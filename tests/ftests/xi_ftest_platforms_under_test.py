from tools.xi_client_settings import XiClientPlatform
from tools.xi_client_settings import XiClientSocketType

# Extend this dictionary if a new platform becomes available for functional tests.
PLATFORMS_UNDER_TEST = {
    'names': [
        #" py2 ",
        " py3 ",
        #" py2_ws ",
        #" py3_ws ",
        #"javascript",
        " C "
        ],
    'values': [
        #{ "platform" : XiClientPlatform.PYTHON_2,   "socket_type" : XiClientSocketType.SOCKET },
         { "platform" : XiClientPlatform.PYTHON_3,   "socket_type" : XiClientSocketType.SOCKET },
        #{ "platform" : XiClientPlatform.PYTHON_2,   "socket_type" : XiClientSocketType.WEBSOCKET },
        #{ "platform" : XiClientPlatform.PYTHON_3,   "socket_type" : XiClientSocketType.WEBSOCKET },
        #{ "platform" : XiClientPlatform.JAVASCRIPT, "socket_type" : XiClientSocketType.WEBSOCKET },
        { "platform" : XiClientPlatform.C,          "socket_type" : XiClientSocketType.SOCKET }
        ]
    }
