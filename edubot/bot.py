"""
Module for AI processing tasks
"""
import openai
from sqlalchemy import select

from edubot import OPENAI_KEY
from edubot.sql import Bot, Completion, Message, Session, Thread
from edubot.types import MessageInfo


class EduBot:
    """
    An AI chatbot which continually improves itself using user feedback.
    """

    def __init__(self, username: str, platform: str, personality: str = ""):
        """
        Initialise EduBot with personalised information about the bot.

        :param username: A unique name to identify this bot from others on the same platform.
        :param platform: The platform the bot is running on E.g. 'telegram' 'matrix' 'mastodon'
        :param personality: Some example conversation to influence the bots personality and mission.
            Must be in "username: message\n ..." format.
        """
        self.username = username
        self.platform = platform
        self.personality = personality

        self.__add_bot_to_db()

        # The primary key of the bot in the database
        self.__bot_pk = self.__get_bot(username).id

        openai.api_key = OPENAI_KEY

    def __get_bot(self, username: str) -> Bot | None:
        """
        Returns the Bot of "username" if it exists on this platform otherwise returns None.
        """
        with Session() as session:
            bot = session.execute(
                select(Bot)
                .where(Bot.username == username)
                .where(Bot.platform == self.platform)
            ).fetchone()

            if bot:
                return bot[0]
            else:
                return None

    def __add_bot_to_db(self) -> None:
        """
        Insert this bot into the DB if it isn't already.
        """
        if not self.__get_bot(self.username):
            with Session() as session:
                new_bot = Bot(username=self.username, platform=self.platform)

                session.add(new_bot)
                session.commit()

    def __get_message(self, msg_info: MessageInfo) -> Message | None:
        """
        Get an ORM Message object from the database.
        """
        with Session() as session:
            message = session.execute(
                select(Message)
                .where(Message.username == msg_info["username"])
                .where(Message.message == msg_info["message"])
                .where(Message.time == msg_info["time"])
                .where(Thread.platform == self.platform)
            ).fetchone()
            if message:
                return message[0]
            else:
                return None

    def __get_thread(self, thread_name: str) -> Thread | None:
        """
        Get an ORM Thread object from the database.
        """
        with Session() as session:
            thread = session.execute(
                select(Thread)
                .where(Thread.thread_name == thread_name)
                .where(Thread.platform == self.platform)
            ).fetchone()

            if thread:
                return thread[0]
            else:
                return None

    def __add_completion(self, completion: str, reply_to: MessageInfo) -> None:
        """
        Add a completion to the database.

        :param completion: The text the bot generated.
        :param reply_to: The message the bot was replying to.
        """
        msg_id = self.__get_message(reply_to).id
        with Session() as session:
            new_comp = Completion(
                bot=self.__bot_pk,
                message=completion,
                reply_to=msg_id,
            )
            session.add(new_comp)
            session.commit()

    def gpt_answer(
        self,
        context: list[MessageInfo],
        thread_name: str,
        personality_override: str = None,
    ) -> str:
        """
        Use chat context to generate a GPT3 response.

        :param context: Chat context as a chronological list of MessageInfo
        :param thread_name: The unique identifier of the thread this context pertains to
        :param personality_override: A custom personality that overrides the default.

        :returns: The response from GPT
        """
        with Session() as session:
            thread = self.__get_thread(thread_name)

            if not thread:
                thread = Thread(thread_name=thread_name, platform=self.platform)

                session.add(thread)
                session.commit()

            for msg in context:
                # If the message is already in the database
                if self.__get_message(msg) is not None:
                    continue

                # If the message was written by a bot
                if self.__get_bot(msg["username"]) is not None:
                    continue

                row: dict = msg
                row["thread"] = thread.id

                session.add(Message(**row))

            session.commit()

        # Construct context for OpenAI completion
        context_str = ""
        for msg in context:
            context_str += f"{msg['username']}: {msg['message']}\n"

        personality = self.personality
        if personality_override:
            personality = personality_override

        if not personality.endswith("\n"):
            personality += "\n"

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=personality + context_str + f"{self.username}: ",
            temperature=0.9,
            max_tokens=900,
            top_p=1,
            frequency_penalty=1.0,
            presence_penalty=0.6,
        )

        completion: str = response["choices"][0]["text"]

        # Strip username from completion
        completion = completion.replace(f"{self.username}: ", "").lstrip()

        # Add a new completion to the database using the completion text and the message being replied to
        self.__add_completion(completion, context[-1])

        # Return the completion result back to the integration
        return completion
