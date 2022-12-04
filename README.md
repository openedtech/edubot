# Edubot

An AI-based bot (currently using GPT-3) designed to be used in various environment (Matrix, Mastodon, etc).

The Edubot, as the name suggests, focussed on use in educational environments:
  1. It is intended to be educational, with a customisable personality for your context.
  1. It can learn from interaction with users.
  
Edubot is the first project from Open EdTech  https://openedtech.global 


## Dev environment quickstart
1. Install [Poetry](https://python-poetry.org/docs/)
1. Install dependencies: `poetry install`
1. Activate the env: `poetry shell`
1. Install pre-commit hooks: `pre-commit install`
1. Copy SAMPLE_CONFIG.ini and put your information in
1. Set the `EDUBOT_CONFIG` env variable to wherever you put your config.
