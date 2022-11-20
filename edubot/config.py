from os import environ

try:
    API_KEY = environ["OPENAI_KEY"]
except KeyError:
    print("OPENAI_KEY environment variable doesn't exist.")
    exit(1)
