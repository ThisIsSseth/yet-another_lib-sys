from enum import Enum, auto

class LoginStatus(Enum):
    LOGGED_OUT = auto()
    STUDENT = auto()
    OPERATOR = auto()
    MANAGER = auto()
    GUEST = auto()
