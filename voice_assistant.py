import helper
import requests
import logging
import constants
from wit import Wit
from pydub import AudioSegment

wit_token = constants.wit_token
client = Wit(wit_token)

def handle_voice_message(sender, voice_url, last_sender_message):
    try:
        helper.reply(sender, "Я получил аудио-сообщение!")
        g = requests.get(voice_url, stream=True)
        voice_filename = "voice_" + sender + ".mp4"
        voice_filename_mp3 = "voice_" + sender + ".mp3"
        with open(voice_filename, "wb") as o:
            o.write(g.content)
        AudioSegment.from_file(voice_filename, "mp4").export(voice_filename_mp3, format="mp3")
        with open(voice_filename_mp3, 'rb') as f:
            try:
                resp = client.speech(f, None, {'Content-Type': 'audio/mpeg3'})
                logging.info('Yay, got Wit.ai response: ' + str(resp))
                if "_text" in resp:
                    message = resp['_text']
                logging.info("Message = " + message)
            except:
                helper.reply(sender, "Извините, я не понял что Вы сказали")
    except:
        logging.error(helper.PrintException())