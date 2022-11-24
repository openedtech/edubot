from __future__ import annotations

from datetime import datetime

import openai
from sqlalchemy import select

from edubot import OPENAI_KEY
from edubot.sql import Message, Session, Thread


class EduBot:
    def __init__(self, bot_name: str, platform: str, personality: str = ""):
        """
        Initialise EduBot with personalised information about the bot.

        :param bot_name: A unique name to identify this bot from others
        :param platform: The platform the bot is running on E.g. 'telegram' 'matrix' 'mastodon'
        :param personality: Some example conversation to influence the bots personality and mission.
            Must be in "username: message\n ..." format.
        """
        self.bot_name = bot_name
        self.platform = platform
        self.personality = personality

    def gpt_answer(
        self, context: list[dict[str, str | datetime]], thread_id: str
    ) -> str:
        """
        Use chat context to generate a GPT3 response.

        :param context: Chat context as list of dicts with attrs: 'username', 'message', and 'time' (as datetime)
        :param thread_id: The ID of the thread this context pertains to

        :returns: The response from GPT
        """
        openai.api_key = OPENAI_KEY

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

                if msg_exists:
                    continue

                if msg["username"] == self.bot_name:
                    msg["by_bot"] = self.bot_name

                session.add(Message(**msg))

            session.commit()

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
        text_response = text_response.replace(f"{self.bot_name}: ", "").lstrip()

        return text_response
