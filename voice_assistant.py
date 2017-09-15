import helper
import requests
import logging
from wit import Wit
from pydub import AudioSegment

def handle_voice_message(sender, voice_url):
    try:
        helper.reply(sender, "Я получил аудио-сообщение!")
        g = requests.get(voice_url, stream=True)
        voice_filename = "voice_" + sender + ".mp4"
        voice_filename_mp3 = "voice_" + sender + ".mp3"
        with open(voice_filename, "wb") as o:
            o.write(g.content)
        AudioSegment.from_file(voice_filename, "mp4").export(voice_filename_mp3, format="mp3")
    except:
        logging.error(helper.PrintException())