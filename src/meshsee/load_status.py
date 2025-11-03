from enum import Enum, auto


class LoadStatus(Enum):
    NONE = auto()
    START = auto()
    COMPLETE = auto()
    ERROR = auto()
    DEBUG = auto()
