from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from edubot import DATABASE

engine = create_engine(DATABASE, echo=True, future=True)

Base = declarative_base()

Session = sessionmaker(engine)


class Thread(Base):
    """
    Table for thread information, every message must belong to a thread.

    A thread is any construct that groups related messages together, E.g. A Forum, chatroom, email thread,
    or replies to a mastodon toot.
    """

    __tablename__ = "thread"

    id = Column(Integer, primary_key=True)

    # The platform the thread belongs to
    platform = Column(String(100), nullable=False)

    # Identifier for this thread that is unique for this platform
    thread_name = Column(String, nullable=False)

    # Delete all messages within this thread if the thread is deleted
    messages = relationship("Message", cascade="all, delete")

    # Threads cannot have the same name on the same platform
    UniqueConstraint(thread_name, platform)


class Message(Base):
    """
    Table for messages not written by Edubot instances.
    """

    __tablename__ = "message"

    id = Column(Integer, primary_key=True)

    # The username which wrote this message
    username = Column(String(100), nullable=False)

    message = Column(String(5000), nullable=False)

    # The time (in UTC) that this message was sent
    time = Column(DateTime(), nullable=False)

    thread = Column(Integer, ForeignKey("thread.id"), nullable=False)

    # Someone cannot write the same message at the same time in the same thread
    UniqueConstraint(username, message, time, thread)


class Completion(Base):
    """
    Table for messages written by EduBot instances.
    """

    __tablename__ = "completion"

    id = Column(Integer, primary_key=True)

    # The bot that wrote this completion
    bot = Column(Integer, ForeignKey("bot.id"), nullable=False)

    # The score of user feedback to this completion
    score = Column(Integer, default=0, nullable=False)

    message = Column(String(5000), nullable=False)

    # The message the bot was replying to
    reply_to = Column(Integer, ForeignKey("message.id"), nullable=False)


class Bot(Base):
    """
    Table for the metadata of EduBot instances.
    """

    __tablename__ = "bot"

    id = Column(Integer(), primary_key=True)

    # The username of the bot
    username = Column(String(100), nullable=False)

    # The platform the bot is running on
    platform = Column(String(100), nullable=False)

    # If a bot is deleted, delete all it's completions
    completions = relationship("Completion", cascade="all, delete")

    # Two bots with the same username cannot operate on the same platform
    UniqueConstraint(username, platform)


# Create Tables if they aren't already
Base.metadata.create_all(engine)
