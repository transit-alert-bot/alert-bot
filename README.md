# Bluesky Transit Alert Bot

This repository contains the code for oc-transpo-alerts.bsky.social, a automated bot providing alerts from OC Transpo's official website.

## Set Up

1. Create a new Bluesky account for your bot on the app or website (https://bsky.app)
2. Generate an App Password for your bot account in [settings](https://bsky.app/settings/app-passwords) (this is just to protect your real password)
3. Make a copy of the example `.env` file by running: `cp config-example.yaml config.yaml`
4. Set your bot's username and app password in `config.yaml`
5. Create a new virtual environment with [`venv`](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) or your favorite package manager.

Using venv:
`python3 -m venv .venv`
`source .venv/bin/activate`
`pip install -r requirements.txt`
When you're done: `deactivate`

## Deploying your bot

For development, it's simplest to just run the bot locally (`python3 main.py`). 

For production, you can set it up as a cron job on your server.

1. Clone this repository
2. [Setup](#set-up) your bot and configuration
3. `crontab -e`
4. Add this configuration

```crontab
# pull changes from the source repository
# every 30 minutes
*/30 * * * * cd alert-bot && git pull >> ~/crontab_log.txt 2>&1
# run the python script using venv
# every 5 minutes
*/5 * * * * cd alert-bot && ./venv/bin/python main.py >> ~/alert_bot_log.txt 2>&1
```

> [!TIP]
> If you'd like to review changes before they get pulled, fork this repository and clone your fork. Remember to sync the fork occasionally for security and bug fixes.

## Troubleshooting

If you encounter any errors (e.g. bot not posting, etc...), in the crontab configuration above it will log it to `~/alert_bot_log.txt`, so check that file for any errors:

```sh
cat ~/alert_bot_log.txt
```

If the error isn't related to your configuration/environment, open an issue and we'll look into it.
