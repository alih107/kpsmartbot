import bot_server
import main
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
                logging.info(helper.PrintException())
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
    try:
        entities = resp['entities']
        for i in entities['intent']:
            if i['confidence'] > 0.5:
                handle_intent(sender, last_sender_message, i['value'])
                return
        helper.reply(sender, "Я не уверена, что именно Вы хотите")
    except:
        helper.reply(sender, "Я не поняла Вашу команду")
        logging.error(helper.PrintException())


def handle_intent(sender, last_sender_message, value):
    try:
        if value == 'greeting':
            helper.reply(sender, "Здравствуйте, " + last_sender_message['first_name'] + "!")
            return
        elif value == 'postamat':
            helper.reply(sender, helper.postamat)
            return
        elif value == 'hybridpost_def':
            helper.reply(sender, helper.hybridpost_def)
            return
        elif value == 'supermarket':
            helper.reply(sender, helper.what_is_supermarket)
            return
        elif value == 'trackbynumber_query':
            helper.reply(sender, helper.trackbynumber_query)
            return
        elif value == 'fastmail_options':
            helper.reply(sender, helper.fastmail_options)
            return
        elif value == 'postamat_how':
            helper.reply(sender, helper.postamat_how)
            return
        elif value == 'hybridpost_time':
            helper.reply(sender, helper.hybridpost_time)
            return
        elif value == 'postamat_info_access':
            helper.reply(sender, helper.postamat_info_access)
            return
        elif value == 'hybridpost_info':
            helper.reply(sender, helper.hybridpost_info)
            return
        elif value == 'trackbynumber':
            helper.reply(sender, helper.trackbynumber)
            return
        elif value == 'redirect':
            helper.reply(sender, helper.redirect)
            return
        elif value == 'redirect_why':
            helper.reply(sender, helper.redirect_why)
            return
        elif value == 'package_how_long':
            helper.reply(sender, helper.package_how_long)
            return
        elif value == 'COMMAND_exchange_rates':
            main.reply_currencies_kursy(sender)
            return
        elif value == 'COMMAND_go_home':
            main.reply_main_menu_buttons(sender)
            return
        elif value == 'COMMAND_card2card':
            bot_server.call_card2card(sender, last_sender_message, 'card2card')
            return
        elif value == 'COMMAND_paymobile':
            bot_server.call_balance(sender, last_sender_message, 'balance')
            return
        elif value == 'COMMAND_payonai':
            bot_server.call_onai(sender, last_sender_message, 'onai')
            return
        elif value == 'COMMAND_sendmessage':
            bot_server.call_sendmessage(sender, last_sender_message, 'send.message')
        else:
            helper.reply(sender, "Я не поняла Вашу команду")
    except:
        logging.error(helper.PrintException())

