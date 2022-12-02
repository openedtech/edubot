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
    __tablename__ = "thread"

    id = Column(Integer, primary_key=True)
    thread_id = Column(
        String,
    )
    platform = Column(String(100), nullable=False)
    messages = relationship("Message", cascade="all, delete")

    UniqueConstraint(thread_id, platform)


class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False)
    message = Column(String(5000), nullable=False)
    time = Column(DateTime(), nullable=False)

    # The bot name that wrote this message if it did
    by_bot = String(100)

    thread_id = Column(String, ForeignKey("thread.id"))


# Create Tables if they aren't already
Base.metadata.create_all(engine)
