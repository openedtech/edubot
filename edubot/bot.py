"""
Module for AI processing tasks
"""
import datetime
import io
import logging

import openai
import PIL
import trafilatura
from openai import OpenAIError
from PIL import Image
from sqlalchemy import desc, select
from stability_sdk.client import StabilityInference, process_artifacts_from_answers
from stability_sdk.utils import generation

from edubot import DREAMSTUDIO_KEY, OPENAI_KEY
from edubot.sql import Bot, Completion, Message, Session, Thread
from edubot.types import CompletionInfo, MessageInfo

# The maximum number of GPT tokens that chat context can be.
# The limit for GPT-4 is 8192.
# We limit to 7800 to allow extra room for the response and the personality.
MAX_GPT_TOKENS = 7200

# Prompt for GPT to summarise web pages
WEB_SUMMARY_PROMPT = (
    "Your input is scraped text from a website. Your job is to summarise the text and post it to a chatroom.\n"
    "Long-form text includes pages such as news articles and blog posts.\n"
    "If the page doesn't contain long-form text return the phrase 'NO CONTENT' and nothing else.\n"
    "If the page DOES contain long-form text return a brief 2 sentence summary of the text content. "
    "This summary will then be sent to users.\n"
)

# Settings for GPT completion generation
GPT_SETTINGS = {"model": "gpt-4", "temperature": 0.3, "max_tokens": 700}

logger = logging.getLogger(__name__)


# TODO: use tiktoken for this, the function is currently inaccurate
def estimate_tokens(text: str) -> int:
    """
    Roughly estimates how many GPT tokens a string is.
    See: https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them

    :return: The estimated amount of tokens.
    """
    # Get two estimates
    est1 = len(text) / 4
    est2 = len(text.split(" ")) * 0.75

    # Average them
    return round((est1 + est2) / 2)


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

        # This variable is lazy loaded
        self.stability_client: StabilityInference | None = None

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

    def __format_context(
        self, context: list[MessageInfo], personality_override: str = None
    ) -> list[dict]:
        """
        Formats chat context to the format expected by GPT.

        :param context: A list of MessageInfo.
        :return: The context as a list of dicts in GPT format.
        """
        personality = self.personality
        if personality_override:
            personality = personality_override

        gpt_context: list[dict] = []

        token_count = 0

        for msg in context:
            if msg["username"] == self.username:
                role = "assistant"
            else:
                role = "user"

            content = f"{msg['username']}: {msg['message']}"
            gpt_context.append({"role": role, "content": content})

            token_count += estimate_tokens(content)

        while token_count > MAX_GPT_TOKENS:
            token_count -= estimate_tokens(gpt_context.pop(0)["content"])

        system_messages = [
            {"role": "system", "content": "You are a chatbot named " + self.username},
            {"role": "system", "content": f"Your personality is: {personality}"},
            {
                "role": "system",
                "content": f"The current year is: {datetime.datetime.now().year}",
            },
            {
                "role": "system",
                "content": f"You use the language model {GPT_SETTINGS['model']}",
            },
        ]

        return system_messages + gpt_context

    # TODO: return None on error instead of empty string.
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
        if not OPENAI_KEY:
            raise RuntimeError(
                "OpenAI key is not defined, make sure to supply it in the config."
            )

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

        gpt_context = self.__format_context(
            context, personality_override=personality_override
        )

        try:
            response = openai.ChatCompletion.create(
                messages=gpt_context,
                **GPT_SETTINGS,
            )
        except OpenAIError as e:
            logger.error(f"OpenAI request failed: {e}")
            return ""

        completion: str = response["choices"][0]["message"]["content"]

        # Strip username from completion
        completion = completion.replace(f"{self.username}: ", "").lstrip()

        # Add a new completion to the database using the completion text and the message being replied to
        self.__add_completion(completion, context[-1])

        # Return the completion result back to the integration
        return completion

    def change_completion_score(
        self, offset: int, completion: CompletionInfo, thread_name: str
    ) -> None:
        """
        Change user feedback to a completion.

        :param offset: An integer representing the new positive or negative votes to this reaction.
        :param completion: Information about the completion being reacted to.
        :param thread_name: A unique identifier for the thread the completion resides in.
        """

        # 1.5 mins before the completion was sent
        delta = completion["time"] - datetime.timedelta(minutes=1, seconds=30)

        with Session() as session:
            # This select statement might get the wrong completion if the bot has sent duplicate messages in the same
            #  thread within 1.5 minutes.
            # BUT this isn't really a problem because it's very likely that users have the same reaction to
            #  both of the duplicate messages.
            # TODO: Is there a way to uniquely identify a bot completion? We can't record the time the completion was
            #  sent as we don't know when the integration sends the completion. The integration also can't know for
            #  sure which message a completion was replying to, as messages can be sent while the bot is generating
            #  responses.
            completion_row = session.execute(
                select(Completion)
                .join(Bot)
                .join(Message)
                .join(Thread)
                .where(Completion.message == completion["message"])
                .where(Thread.thread_name == thread_name)
                .where(Bot.id == self.__bot_pk)
                # The message being replied to was sent not more than 1.5 minutes before the completion
                .where(delta < Message.time)
                .where(Message.time < completion["time"])
                .order_by(desc(Completion.id))
            ).fetchone()

            if not completion_row:
                logger.debug(
                    f"Message is not a GPT completion: '{completion['message']}' @ {completion['time']}"
                )
                return

            completion: Completion = completion_row[0]

            completion.score += offset

            session.add(completion)
            session.commit()

            logger.info(f"Completion {completion.id} incremented by {offset}.")

    def generate_image(self, prompt: str) -> Image.Image | None:
        """
        Generate an image using Stability AI's DreamStudio.

        :param prompt: A description of the image that should be generated.
        :return: A PIL.Image instance.
        """
        if not DREAMSTUDIO_KEY:
            raise RuntimeError(
                "DreamStudio key is not defined, make sure to supply it in the config."
            )

        # Lazy load client
        if self.stability_client is None:
            verbose = logger.level >= 10
            self.stability_client = StabilityInference(
                key=DREAMSTUDIO_KEY, verbose=verbose
            )

        # Get Answer objects from stability
        answers = self.stability_client.generate(prompt)

        # Convert answer objects into artifacts we can use
        artifacts = process_artifacts_from_answers("", "", answers, write=False)

        try:
            for _, artifact in artifacts:
                # Check that the artifact is an Image, not sure why this is necessary.
                # See: https://github.com/Stability-AI/stability-sdk/blob/d8f140f8828022d0ad5635acbd0fecd6f6fc317a/src/stability_sdk/utils.py#L80
                if artifact.type == generation.ARTIFACT_IMAGE:
                    img = PIL.Image.open(io.BytesIO(artifact.binary))
                    return img
        # Exception only happens when prompt is inappropriate.
        except Exception:
            return None

    def summarise_url(self, url: str, msg: MessageInfo, thread_name: str) -> str | None:
        """
        Use GPT to summarise the text content of a URL.

        Returns None if the webpage cannot be fetched or doesn't contain long-form text to summarise.

        :param url: A valid url.
        :param msg: The message that triggered this summary request.
        :param thread_name: A unique identifier for the thread the URL was sent in.
        """
        resp = trafilatura.fetch_url(url)

        # If HTTP or network error
        if resp == "" or resp is None:
            return None

        # Convert HTML to Plaintext
        text = trafilatura.extract(resp)

        # If error converting to plaintext
        if text is None:
            return None

        # Ensure text doesn't exceed GPT limits
        while estimate_tokens(text) > MAX_GPT_TOKENS:
            text = text[:-100]

        gpt_context = [
            {"role": "system", "content": WEB_SUMMARY_PROMPT},
            {"role": "user", "content": text},
        ]
        try:
            completion = openai.ChatCompletion.create(
                messages=gpt_context,
                **GPT_SETTINGS,
            )
        except OpenAIError as e:
            logger.error(f"OpenAI request failed: {e}")
            return None

        completion_text: str = completion["choices"][0]["message"]["content"]

        if "NO CONTENT" in completion_text.upper():
            return

        completion_text = completion_text.strip()

        with Session() as session:
            thread = self.__get_thread(thread_name)
            if not thread:
                thread = Thread(thread_name=thread_name, platform=self.platform)
                session.add(thread)
                session.commit()

            if self.__get_message(msg) is None:
                row: dict = msg
                row["thread"] = thread.id
                session.add(Message(**row))
                session.commit()

            # Ensure URL summaries are added to the DB
            self.__add_completion(completion_text, msg)

            session.commit()

        return completion_text
