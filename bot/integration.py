"""
Everything related to Integration implementation
"""
import abc
import threading
from abc import abstractmethod


class Integration(abc):
    """
    Integration logic that can be called by the bot to use different integrations.

    Network errors, should be caught and logged so that an error with the integration doesn't crash the thread.
    When an error occurs, getter methods should return None and setter methods should return False.
    """
    class EventThread(threading.Thread):
        """
        A thread for handling integration specific events.
        """
        pass

    def __init__(self):
        """
        Initialise an integration.
        """
        # Self.name should be set to a unique identifier for your integration.
        # e.g. "matrix" or "mastodon"
        self.name: str = ""
        pass

    def name(self) -> str:
        """
        """
        pass

    @abstractmethod
    def send_message(self, message: str, thread_id: str, formatted: bool = False) -> bool:
        """
        Send `message` to the thread of `thread_id`

        :param message: The message to send
        :param thread_id: The thread ID
        :param formatted: True indicates the message is formatted in Markdown
        """
        pass

    @abstractmethod
    def send_reaction(self, emoji: str, thread_id: str, message_id: str) -> bool:
        """
        Send a `reaction` to `message_id` in `thread_id`.

        :param emoji: A unicode emoji
        :param thread_id: The thread ID
        :param message_id: The message ID
        """
        pass



# A dictionary mapping the integration names to their instances
# e.g. {"matrix": Matrix(), "mastodon": Mastodon()}
integrations: list[Integration] = []

def start_threads() -> None:
    for i in integrations:
        i.EventThread(name=i.name)

