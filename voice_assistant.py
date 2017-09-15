import helper
import requests
import logging
from wit import Wit
from pydub import AudioSegment

def handle_voice_message(sender, voice_url):
    logging.info(voice_url)
    try:
        helper.reply(sender, "Я получил аудио-сообщение!")
    except:
        logging.error(helper.PrintException())