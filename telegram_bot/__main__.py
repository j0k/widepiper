#!/usr/bin/env python3


import os
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler

from . import handlers


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token is None:
        logger.critical("TELEGRAM_BOT_TOKEN environment variable is unset")
        return

    webapp_url = os.getenv("WEBAPP_URL")
    if webapp_url is None:
        logger.critical("WEBAPP_URL environment variable is unset")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", handlers.start_command))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("app", handlers.app_command))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
