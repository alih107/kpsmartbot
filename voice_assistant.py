import helper
import requests
import logging
from wit import Wit
from pydub import AudioSegment

def handle_voice_message(sender, data):
    logging.info("Handling audio...")
    try:
        helper.reply(sender, "Я получил аудио-сообщение!")
    except:
        logging.error(helper.PrintException())