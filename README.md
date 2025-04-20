# OC Transpo Alerts Bot

This repository contains the code for oc-transpo-alerts.bsky.social, a automated bot providing alerts from OC Transpo's official website.

## Set Up

1. Create a new Bluesky account for your bot on the app or website (https://bsky.app)
2. Generate an App Password for your bot account in [settings](https://bsky.app/settings/app-passwords) (this is just to protect your real password)
3. Make a copy of the example `.env` file by running: `cp .env.example .env`
4. Set your bot's username and app password in `.env`
5. Create a new virtual environment with [`venv`](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) or your favorite package manager.

Using venv:
`python3 -m venv .venv`
`source .venv/bin/activate`
`pip install -r requirements.txt`
When you're done: `deactivate`

## Deploying your bot

For development, it's simplest to just run the bot locally (`python3 main.py`). When you want to deploy it for real, there are many free or low cost cloud hosting options like [Heroku](https://devcenter.heroku.com/articles/github-integration) or [Fly.io](https://fly.io/docs/reference/fly-launch/).
