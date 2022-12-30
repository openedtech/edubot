"""
Custom types
"""
from datetime import datetime
from typing import TypedDict


class MessageInfo(TypedDict):
    """
    Represents a message in a thread.
    """

    username: str
    message: str
    time: datetime


class CompletionInfo(TypedDict):
    """
    Represents a bot response to a message.
    """

    message: str
    time: datetime
