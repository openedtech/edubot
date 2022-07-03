import logging
from random import random

from nio import AsyncClient, MatrixRoom, RoomMessageText

from moodlebot import gpt, g
from moodlebot.chat_functions import send_text_to_room
from moodlebot.config import Config
from moodlebot.storage import Storage

logger = logging.getLogger(__name__)


class Message:
    def __init__(
          self,
          client: AsyncClient,
          store: Storage,
          config: Config,
          message_content: str,
          room: MatrixRoom,
          event: RoomMessageText,
    ):
        """Initialize a new Message

        Args:
            client: nio client used to interact with matrix.

            store: Bot storage.

            config: Bot configuration parameters.

            message_content: The body of the message.

            room: The room the event came from.

            event: The event defining the message.
        """
        self.client = client
        self.store = store
        self.config = config
        self.message_content = message_content
        self.room = room
        self.event = event

    async def process(self) -> None:
        """Process and possibly respond to the message"""
        if self._check_if_response():
            await self._respond()

    def _check_if_response(self):
        if "moodlebot" in self.message_content.lower():
            return True

        if self.room.member_count <= 2:
            return True

        if random() < 0.5:
            return True

        return False

        pass

    async def _respond(self):
        limit = 20
        if "moodlebot" != self.message_content.lower() or self.room.member_count <= 2:
            limit = 200

        messages = await self.client.room_messages(self.room.room_id, self.client.loaded_sync_token, limit=limit)
        username = self.event.sender[1:].split(":")[0]
        response = gpt.process_query(messages, username + ": " + self.message_content.lower())

        await send_text_to_room(self.client, self.room.room_id, response)
