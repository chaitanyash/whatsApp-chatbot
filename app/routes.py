from flask import Blueprint, request
from app.bot import process_message

bot = Blueprint("bot", __name__)


@bot.route("/bot", methods=["POST"])
def index():
    incoming_msg = request.values.get("Body", "").strip().lower()
    remote_number = request.values.get("From", "")

    bot_response = process_message(incoming_msg, remote_number)
    return bot_response