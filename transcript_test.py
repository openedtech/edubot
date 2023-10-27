from edubot import transcription

t = transcription.Transcriber("/home/tom/Downloads/meeting_test.mp4")
# t = transcription.Transcriber("https://recordings.reu1.blindsidenetworks.com/openedtech/25d591b9102faed0e4bb27cfae9d46295b70e3df-1690373226728/capture/capture-0.m4v")
# t = transcription.Transcriber("https://media.blubrry.com/culips/content.blubrry.com/culips/B073_HistoryLesson.mp3")

print(t.summarise_transcript())
