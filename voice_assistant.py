import helper
import requests
import logging
from wit import Wit
from pydub import AudioSegment

def handle_voice_message(sender, voice_url):
    try:
        helper.reply(sender, "Я получил аудио-сообщение!")
        g = requests.get(voice_url, stream=True)
        logging.info(g)
    except:
        logging.error(helper.PrintException())