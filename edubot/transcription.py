"""
Audio transcription using Whisper.
"""
# TODO: Integrate as a plugin for Edubot
import json
from os import PathLike
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryFile

import replicate
import requests
from langchain.prompts import ChatPromptTemplate
from moviepy.video.io.VideoFileClip import VideoFileClip

from edubot import HUGGING_FACE_KEY
from edubot.bot import LLM

prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a summarising bot. Humans provide you with transcripts from meetings and conversations. "
            "Your job is to summarise the transcripts, pulling out the key points without using the names of "
            "the speakers in your summaries.",
        ),
        (
            "human",
            "Summarise the following transcript in a few paragraphs. "
            "You must pull out the key points of discussion without using the names of the speakers. "
            "Here is the transcript: {transcript}",
        ),
    ]
)


class Transcriber:
    def __init__(self, video_file: PathLike | str):
        """
        Initialise the transcriber.
        :param video_file: Supply either the path to a local file, or the URL where the content is hosted.
        """
        self.video_file = video_file
        self.audio_file = None
        self.transcript = ""
        self.is_local_file = True

        # TODO: Better way of determining is content is URL?
        if video_file.startswith("http"):
            self.is_local_file = False

    def __str__(self):
        if self.transcript:
            return f"Transcription of audio file {self.audio_file}"
        return f"Empty Transcriber {id(self)}"

    def generate_transcription(self):
        if self.transcript:
            return self.transcript

        fp = self.video_file

        temp_vid_file = NamedTemporaryFile()
        if not self.is_local_file:
            resp = requests.get(self.video_file)
            temp_vid_file.write(resp.content)
            fp = Path(temp_vid_file)

        audio = self.strip_audio_from_video_file(fp)

        if not self.is_local_file:
            temp_vid_file.close()

        self.transcript = self.__transcribe_audio(audio)

        audio.close()

        return self.transcript

    def summarise_transcript(self):
        if not self.transcript:
            self.generate_transcription()

        return LLM(prompt_template.format_messages(transcript=self.transcript)).content

    # TODO: Figure out how to process the dict returned by transcribe()
    @staticmethod
    def __transcribe_audio(audio_file: NamedTemporaryFile) -> str:
        """
        Transcribe an audio file and return a transcript with speakers identified.
        """
        json_resp = replicate.run(
            "mymeetai/whisperx-speakers:7a52a429991110f98d7a086a5c98dd6b773224a4695afdaab6f19fafbcea5845",
            input={
                "audio": open(audio_file.name, "rb"),
                "hugging_face_token": HUGGING_FACE_KEY,
                "debug": True,
            },
        )

        sentences = json.loads(json_resp)
        transcript = ""
        for sentence in sentences[0]:
            transcript += f"{sentence['speaker']}: {sentence['text']}\n"

        return transcript

    @staticmethod
    def strip_audio_from_video_file(video_file) -> TemporaryFile:
        audio = VideoFileClip(video_file).audio
        temp_file = NamedTemporaryFile(suffix=".wav")

        audio.write_audiofile(temp_file.name, codec="pcm_s16le")
        return temp_file
