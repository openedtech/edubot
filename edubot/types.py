"""
Custom types
"""
# TODO: Consider replacing these with langchain objects/db
from datetime import datetime
from typing import TypedDict

import PIL.Image


class MessageInfo(TypedDict):
    """
    Represents a message in a thread.
    """

    username: str
    message: str
    time: datetime


class ImageInfo(TypedDict):
    """
    Represents an image in a thread.

    This class is only used for processing images to text. Only the AI generated caption is stored in the database.
    """

    username: str
    image: PIL.Image.Image
    time: datetime


class CompletionInfo(TypedDict):
    """
    Represents a bot response to a message.
    """

    message: str
    time: datetime
