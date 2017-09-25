import bot_server
import main
import helper
import requests
import logging
import constants
import os
import feedparser
import time
from random import randint

from wit import Wit
from pydub import AudioSegment

wit_token = constants.wit_token
client = Wit(wit_token)

def handle_voice_message(sender, voice_url, last_sender_message):
    logging.info("Handling audio")
    try:
        main.reply_typing_on(sender)
        start = time.time()
        g = requests.get(voice_url, stream=True)
        logging.info('requests.get(voice_url) time = ' + str(time.time() - start))
        voice_filename = "voice_" + sender + ".mp4"
        voice_filename_mp3 = "voice_" + sender + ".mp3"
        with open(voice_filename, "wb") as o:
            start = time.time()
            o.write(g.content)
            logging.info('o.write(g.content) time = ' + str(time.time() - start))
        start = time.time()
        AudioSegment.from_file(voice_filename, "mp4").export(voice_filename_mp3, format="mp3")
        logging.info('AudioSegment export time = ' + str(time.time() - start))
        with open(voice_filename_mp3, 'rb') as f:
            try:
                start = time.time()
                resp = client.speech(f, None, {'Content-Type': 'audio/mpeg3'})
                logging.info('Wit.ai client.speech response time = ' + str(time.time() - start))
                logging.info('Yay, got Wit.ai response: ' + str(resp))
                handle_entities(sender, last_sender_message, resp)
            except:
                logging.info(helper.PrintException())
                main.reply(sender, "Извините, я не поняла что Вы сказали")
        main.reply_typing_off(sender)
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
        main.reply(sender, "Я не уверена, что именно Вы хотите")
    except:
        main.reply(sender, "Я не поняла Вашу команду")
        logging.error(helper.PrintException())


def handle_intent(sender, last_sender_message, value):
    try:
        if value == 'greeting':
            message = "Здравствуйте, " + last_sender_message['first_name'] + "!\n"
            message += "Меня зовут Е-Сауле, я голосовая помощница этого бота."
            main.reply(sender, message)
        elif value == 'postamat':
            main.reply(sender, helper.postamat)
        elif value == 'hybridpost_def':
            main.reply(sender, helper.hybridpost_def)
        elif value == 'supermarket':
            main.reply(sender, helper.what_is_supermarket)
        elif value == 'trackbynumber_query':
            main.reply(sender, helper.trackbynumber_query)
        elif value == 'fastmail_options':
            main.reply(sender, helper.fastmail_options)
        elif value == 'postamat_how':
            main.reply(sender, helper.postamat_how)
        elif value == 'hybridpost_time':
            main.reply(sender, helper.hybridpost_time)
        elif value == 'postamat_info_access':
            main.reply(sender, helper.postamat_info_access)
        elif value == 'hybridpost_info':
            main.reply(sender, helper.hybridpost_info)
        elif value == 'trackbynumber':
            main.reply(sender, helper.trackbynumber)
        elif value == 'redirect':
            main.reply(sender, helper.redirect)
        elif value == 'redirect_why':
            main.reply(sender, helper.redirect_why)
        elif value == 'package_how_long':
            main.reply(sender, helper.package_how_long)
        elif value == 'COMMAND_exchange_rates':
            main.reply_currencies_kursy(sender)
        elif value == 'COMMAND_go_home':
            main.reply_main_menu_buttons(sender)
        elif value == 'COMMAND_card2card':
            bot_server.call_card2card(sender, last_sender_message, 'card2card')
        elif value == 'COMMAND_paymobile':
            bot_server.call_balance(sender, last_sender_message, 'balance')
        elif value == 'COMMAND_payonai':
            bot_server.call_onai(sender, last_sender_message, 'onai')
        elif value == 'COMMAND_sendmessage':
            bot_server.call_sendmessage(sender, last_sender_message, 'send.message')
        elif value == 'COMMAND_my_cards':
            bot_server.call_addcard(sender, last_sender_message, 'addcard')
        elif value == 'COMMAND_nearest':
            main.reply_nearest(sender)
        elif value == 'COMMANDS_nearest_postamat' or value == 'find_postamat':
            bot_server.call_request_nearest_location(sender, last_sender_message, 'nearest.postamats')
        elif value == 'COMMANDS_nearest_office' or value == 'find_dep':
            bot_server.call_request_nearest_location(sender, last_sender_message, 'nearest.offices')
        elif value == 'COMMANDS_nearest_atm':
            bot_server.call_request_nearest_location(sender, last_sender_message, 'nearest.atms')
        elif value == 'COMMAND_nearest':
            main.reply_nearest(sender)
        elif value == 'COMMAND_disable_bot':
            bot_server.call_disable_bot(sender, last_sender_message, 'disable.bot')
        elif value == 'penalties_pdd' or value == 'COMMAND_penalties':
            main.reply_pdd_shtrafy(sender)
        elif value == 'info_post':
            bot_server.call_tracking(sender, last_sender_message, 'tracking')
        elif value == 'how_are_you':
            main.reply(sender, "У меня всё замечательно!")
        elif value == 'FUN_anekdot':
            r = feedparser.parse('http://anekdotme.ru/RSS')
            random_int = randint(0, len(r['entries']) - 1)
            anekdot = r['entries'][random_int]['summary_detail']['value']
            anekdot = anekdot.replace('<br />', '\n').replace('&mdash;', '').replace('<BR>', '').replace('<br>', '')
            logging.info("Anekdot = " + anekdot)
            main.reply(sender, anekdot)
            pass
        else:
            main.reply(sender, "Я не поняла Вашу команду")
    except:
        logging.error(helper.PrintException())

