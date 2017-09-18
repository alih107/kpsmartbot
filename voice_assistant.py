import helper
import requests
import logging
import constants
import os
from wit import Wit
from pydub import AudioSegment

wit_token = constants.wit_token
client = Wit(wit_token)

def handle_voice_message(sender, voice_url, last_sender_message):
    try:
        helper.reply_typing_on(sender)
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
                handle_entities(sender, last_sender_message, resp)
            except:
                helper.reply(sender, "Извините, я не поняла что Вы сказали")
        helper.reply_typing_off(sender)
        try:
            os.remove(voice_filename)
            os.remove(voice_filename_mp3)
        except:
            pass
    except:
        logging.error(helper.PrintException())

def handle_entities(sender, last_sender_message, resp):
    entities = resp['entities']
    try:
        i = entities['intent']
        if i['confidence'] > 0.7:
            handle_intent(sender, last_sender_message, i['value'])
            return
    except:
        pass


def handle_intent(sender, last_sender_message, value):
    if value == 'greeting':
        helper.reply(sender, "Здравствуйте, " + last_sender_message['first_name'])
        return

