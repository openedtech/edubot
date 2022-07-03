from random import random
from nio import AsyncClient, MatrixRoom, RoomMessageText, MessageDirection

from moodlebot import gpt, g
from moodlebot.chat_functions import react_to_event, send_text_to_room
from moodlebot.config import Config
from moodlebot.storage import Storage


class Command:
    def __init__(
          self,
          client: AsyncClient,
          store: Storage,
          config: Config,
          command_and_args: str,
          room: MatrixRoom,
          event: RoomMessageText,
    ):
        """A command made by a user.

        Args:
            client: The client to communicate to matrix with.

            store: Bot storage.

            config: Bot configuration parameters.

            command_and_args: The command and arguments.

            room: The room the command was sent in.

            event: The event describing the command.
        """
        self.client = client
        self.store = store
        self.config = config
        self.command = command_and_args.split()[0]
        self.room = room
        self.event = event
        self.args = command_and_args.split()[1:]

    async def process(self):
        """Process the command"""
        if self.event.sender not in g.config.admins:
            return

        if self.command == "help":
            await self._show_help()
        elif self.command == "greeting":
            await self._greeting()
        else:
            await self._unknown_command()

    async def _show_help(self):
        """Show the help text"""
        await send_text_to_room(
            self.client,
            self.room.room_id,
            (f"#Admin commands:\n"
             f"`{g.config.command_prefix}greeting [msg]` change MoodleBot's greeting, if no msg is supplied the "
             f"current greeting is shown "
             ))

    async def _unknown_command(self):
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown command '{self.command}'. Try the 'help' command for more information.",
        )

    async def _greeting(self):
        if len(self.args) > 0:
            g.config.greeting = " ".join(self.args)
            with open("GREETING", "w") as f:
                f.write(g.config.greeting)
            await send_text_to_room(self.client, self.room.room_id, "New greeting set!")
        else:
            await send_text_to_room(self.client, self.room.room_id, g.config.greeting)
