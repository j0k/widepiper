import os
from telegram import (
    Update,
    WebAppInfo,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
)


async def start_command(update: Update, ctx):
    await standart_webapp_response(update, ctx)


async def help_command(update, ctx):
    await update.message.reply_text("""/app - получить ссылку на приложение""")


async def app_command(update: Update, ctx):
    await standart_webapp_response(update, ctx)


async def standart_webapp_response(update: Update, ctx):
    webapp_url = os.getenv("WEBAPP_URL")
    menu_button = MenuButtonWebApp("Приложение", WebAppInfo(webapp_url))
    await update.effective_user.set_menu_button(menu_button=menu_button)

    keyboard_markup = InlineKeyboardMarkup.from_button(
        InlineKeyboardButton(
            text="Приложение",
            web_app=WebAppInfo(url=webapp_url),
        )
    )
    await update.message.reply_text("Открыть приложение:", reply_markup=keyboard_markup)
