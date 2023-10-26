from edubot import transcription

t = transcription.Transcriber("/home/tom/Downloads/test_vid.mp4")
# t = transcription.Transcriber("https://media.blubrry.com/culips/content.blubrry.com/culips/B073_HistoryLesson.mp3")

print(t.summarise_transcript())
