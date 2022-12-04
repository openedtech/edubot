from __future__ import annotations

from datetime import datetime

import openai
from sqlalchemy import select

from edubot import OPENAI_KEY
from edubot.sql import Bot, Completion, Message, Session, Thread
from edubot.types import MessageInfo


class EduBot:
    def __init__(self, bot_name: str, platform: str, personality: str = ""):
        """
        Initialise EduBot with personalised information about the bot.

        :param bot_name: A unique name to identify this bot from others.
        :param platform: The platform the bot is running on E.g. 'telegram' 'matrix' 'mastodon'
        :param personality: Some example conversation to influence the bots personality and mission.
            Must be in "username: message\n ..." format.
        """
        self.bot_name = bot_name
        self.platform = platform
        self.personality = personality

        self.__add_bot_to_db()
        self.bot_id = self.__get_bot_id()

        openai.api_key = OPENAI_KEY

    def __add_bot_to_db(self) -> None:
        """
        Insert this bot into the DB if it isn't already.
        """
        if not self.__check_if_bot(self.bot_name):
            with Session() as session:
                new_bot = Bot(name=self.bot_name, platform=self.platform)

                session.add(new_bot)
                session.commit()

    def __get_bot(self, username: str) -> bool:
        """
        Get a bot by username.
        """
        with Session() as session:
            bot = session.execute(
                select(Bot)
                .where(Bot.name == username)
                .where(Bot.platform == self.platform)
            ).fetchone()

            return bool(bot)

    def __get_bot_id(self):
        pass

    def __get_message(self, username: str, time: datetime) -> Message:
        """
        Get an ORM Message object from the database.
        """
        with Session() as session:
            message = session.execute(
                select(Message).where(username == username).where(time == time)
            ).fetchone()

            return message

    def __add_completion(self, completion: str, reply_to: MessageInfo) -> None:
        """
        Add a completion to the database.

        :param completion: The text the bot generated.
        :param reply_to: The message the bot was replying to.
        """
        msg_id = self.__get_message(reply_to["username"], reply_to["time"]).id
        with Session() as session:
            new_comp = Completion(bot)

    def gpt_answer(self, context: list[MessageInfo], thread_id: str) -> str:
        """
        Use chat context to generate a GPT3 response.

        :param context: Chat context as a chronological list of MessageInfo
        :param thread_id: The ID of the thread this context pertains to

        :returns: The response from GPT
        """
        with Session() as session:
            thread = session.execute(
                select(Thread)
                .where(Thread.thread_id == thread_id)
                .where(Thread.platform == self.platform)
            ).fetchone()
            if not thread:
                thread = Thread(thread_id=thread_id, platform=self.platform)

                session.add(thread)

            for msg in context:
                msg_exists = bool(
                    session.execute(
                        select(Message)
                        .where(Message.username == msg["username"])
                        .where(Message.message == msg["message"])
                        .where(Message.time == msg["time"])
                    ).fetchone()
                )

                # If the message exists, or the message was written by an instance of edubot
                # TODO:
                if msg_exists or self.__get_bot(msg["username"]):
                    continue

                session.add(Message(**msg, thread_id=thread_id))

            session.commit()

        # Construct context for OpenAI completion
        context_str = ""
        for msg in context:
            context_str += f"{msg['username']}: {msg['message']}\n"

        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=self.personality + context_str + f"{self.bot_name}: ",
            temperature=0.9,
            max_tokens=750,
            top_p=1,
            frequency_penalty=1.0,
            presence_penalty=0.6,
        )

        text_response: str = response["choices"][0]["text"]

        self.__add_completion(text_response, context[-1])

        text_response = text_response.replace(f"{self.bot_name}: ", "").lstrip()

        return text_response
