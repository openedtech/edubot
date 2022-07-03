from __future__ import annotations

import openai
from nio import RoomMessagesResponse, BadEvent, UnknownBadEvent, RoomMessage, RoomMessageText
from openai import InvalidRequestError

from moodlebot import g


def process_events(messages: RoomMessagesResponse) -> str:
    """
    Convert list of events into a string
    """
    conversation = ""
    messages_lst = [i for i in messages.chunk if isinstance(i, RoomMessageText)]

    for event in reversed(messages_lst):
        # Get username from full ID
        username = event.sender[1:].split(":")[0]
        conversation += "\n" + username + ": " + event.body

    return conversation + "\n"


def process_query(context_events: RoomMessagesResponse, prompt: str):
    """
    Takes a query string (usually a question) and a prompt string, passes it to OpenAI, and returns a response
    """
    openai.api_key = g.config.openai_key
    context = process_events(context_events)

    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=context + g.config.original_prompt + prompt + "\nMoodleBot: ",
        temperature=0.9,
        max_tokens=500,
        top_p=1,
        frequency_penalty=1.0,
        presence_penalty=0.6,
        stop=["Human:"],
    )

    text_response: str = response["choices"][0]["text"]
    text_response = text_response.replace("MoodleBot: ", "").lstrip()

    return text_response
