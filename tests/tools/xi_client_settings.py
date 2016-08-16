from enum import Enum

# Enum class for client types
class XiClientPlatform(Enum):
    C           = 1
    PYTHON_2    = 2
    PYTHON_3    = 3
    JAVASCRIPT  = 4
    JAVA        = 5

class XiClientSocketType(Enum):
    SOCKET        = 0
    WEBSOCKET     = 1
