"""
Audio transcription using Whisper.
"""
# TODO: Integrate as a plugin for Edubot
import json
from os import PathLike
from tempfile import NamedTemporaryFile

import replicate
import requests
import tiktoken
from langchain.prompts import ChatPromptTemplate
from moviepy.video.io.VideoFileClip import VideoFileClip
from pydub import AudioSegment

from edubot import HUGGING_FACE_KEY
from edubot.bot import LLM

transcript_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a summarising bot. Humans provide you with transcripts from meetings and conversations. "
            "Your job is to summarise the transcripts, pulling out the key points without using the names of "
            "the speakers in your summaries. Make your summaries as brief as possible",
        ),
        (
            "human",
            "Summarise the following transcript in a few paragraphs. "
            "You must pull out the key points of discussion without using the names of the speakers. "
            "Here is the transcript: {transcript}",
        ),
    ]
)
shortening_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a bot designed to reduce the length of meeting transcripts. You should remove "
            "extraneous information from the transcripts you are provided. "
            "DO NOT PROVIDE A SUMMARY AND MAINTAIN THE FORMATTING OF THE INPUT DATA! "
            "Only remove personal anecdotes, greetings and unimportant pleasantries to reduce the length of the "
            "transcript.",
        ),
        (
            "human",
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

        temp_vid_file = NamedTemporaryFile(suffix=f".{self.video_file[-3:]}")
        if not self.is_local_file:
            resp = requests.get(self.video_file)

            temp_vid_file.write(resp.content)
            fp = temp_vid_file.name

        audio_segments = self.strip_audio_from_video_file(fp)

        temp_vid_file.close()

        if len(audio_segments) == 1:
            self.transcript = self.__transcribe_audio(audio_segments[0])
            audio_segments[0].close()
        else:
            transcripts = []
            for segment in audio_segments:
                long_transcript = self.__transcribe_audio(segment)
                transcripts.append(self.__shorten_transcript(long_transcript))
                segment.close()

            for t in transcripts:
                self.transcript += t
                self.transcript += "\n"

        return self.transcript

    def __shorten_transcript(self, transcript):
        return LLM(
            shortening_prompt_template.format_messages(transcript=transcript)
        ).content

    def summarise_transcript(self):
        if not self.transcript:
            self.generate_transcription()
        return LLM(
            transcript_prompt_template.format_messages(transcript=self.transcript)
        ).content

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
    def strip_audio_from_video_file(video_file) -> list[NamedTemporaryFile]:
        audio = VideoFileClip(video_file).audio
        temp_file = NamedTemporaryFile(
            prefix="transcript_delete", suffix=".mp3", delete=False
        )
        audio.write_audiofile(temp_file.name)

        # If longer than 10 minutes cut into 10 minute slices
        if audio.duration / 60 > 10:
            segments = []
            audio_segment = AudioSegment.from_file(temp_file, codec="mp3")

            temp_file.delete = True
            temp_file.close()

            # Iterate through every ten minutes of the file
            for time in range(0, int(audio_segment.duration_seconds * 1000), 600000):
                try:
                    audio_slice = audio_segment[time : time + 600000]
                except IndexError:
                    audio_slice = audio_segment[
                        time : audio_segment.duration_seconds * 1000
                    ]
                slice_file_handle = NamedTemporaryFile(suffix=".mp3")
                audio_slice.export(slice_file_handle.name, format="mp3")
                segments.append(slice_file_handle)

            return segments
        else:
            return [temp_file]
