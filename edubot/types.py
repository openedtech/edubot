"""
Custom types
"""
from datetime import datetime
from typing import TypedDict


class MessageInfo(TypedDict):
    username: str
    message: str
    time: datetime
