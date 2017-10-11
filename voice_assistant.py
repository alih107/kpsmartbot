from services import shtrafy
from services import tracking
from finances import mobile
from finances import card2card
from finances import onai
import bot_server
import main
import helper
import constants

import requests
import logging
import os
import feedparser
import time
from random import randint
import xml.etree.ElementTree as ET
from wit import Wit
from pydub import AudioSegment

wit_token = constants.wit_token
client = Wit(wit_token)
uuid = constants.uuid
api_key = constants.api_key

payload_dict = {'balance': 'номер телефона', 'mobile.amount': 'сумму', 'card2card': 'номер карты',
                'card2card.amount': 'сумму', 'onai': 'номер карты Онай', 'onai.amount': 'сумму'}

def yandex_api_post(voice_filename_wav, topic, lang=None):
    headers = {'Content-Type': 'audio/x-wav'}
    url = 'http://asr.yandex.net/asr_xml?uuid=' + uuid + '&key=' + api_key + '&topic=' + topic
    if lang == 'en-US':
        url += '&lang=' + lang
    return requests.post(url, data=open(voice_filename_wav, 'rb'), headers=headers)

def handle_voice_message_yandex(sender, voice_url, last_sender_message):
    main.reply_typing_on(sender)
    try:
        count = 0
        g = requests.get(voice_url, stream=True)
        while g.status_code != 200 and count < 10:
            g = requests.get(voice_url, stream=True)
            count += 1
            logging.info("Couldn't get file from voice_url, try # " + str(count))
        if g.status_code != 200:
            main.reply(sender, "Произошла ошибка при обработке аудио-сообщения, попробуйте ещё раз")
            return
        voice_filename = "voice_" + sender + ".mp4"
        voice_filename_wav = "voice_" + sender + ".wav"
        with open(voice_filename, "wb") as o:
            o.write(g.content)
        try:
            AudioSegment.from_file(voice_filename, "mp4").export(voice_filename_wav, format="wav")  # android
        except:
            AudioSegment.from_file(voice_filename, "aac").export(voice_filename_wav, format="wav")  # iphone
        try:
            payload = last_sender_message['payload']
            if payload in payload_dict:
                logging.info('Trying yandex API with topic numbers ...')
                r = yandex_api_post(voice_filename_wav, 'numbers')
                root = ET.fromstring(r.text)
                logging.info(str(root.tag) + " | " + str(root.attrib))
                if root.attrib['success'] == '0':
                    main.reply(sender, "Пожалуйста, продиктуйте ещё раз " + payload_dict[payload])
                else:
                    for child in root:
                        logging.info(str(child.tag) + " | " + str(child.attrib) + " | " + child.text)
                    yandex_numbers = helper.extract_digits(root[0].text)
                    if payload == 'balance':
                        mobile.reply_mobile_check_number(sender, yandex_numbers, last_sender_message, is_voice=True)
                    elif payload == 'mobile.amount':
                        mobile.reply_mobile_amount(sender, yandex_numbers, last_sender_message, is_voice=True)
                    elif payload == 'card2card':
                        card2card.reply_card2card_check_cardDst(sender, yandex_numbers, last_sender_message, is_voice=True)
                    elif payload == 'card2card.amount':
                        card2card.reply_card2card_amount(sender, yandex_numbers, last_sender_message, is_voice=True)
                    elif payload == 'onai':
                        onai.reply_onai(sender, yandex_numbers, last_sender_message, is_voice=True)
                    elif payload == 'onai.amount':
                        onai.reply_onai_amount(sender, yandex_numbers, last_sender_message, is_voice=True)

            else:
                logging.info('Trying yandex API with topic queries ...')
                r = yandex_api_post(voice_filename_wav, 'queries')
                root = ET.fromstring(r.text)
                logging.info(str(root.tag) + " | " + str(root.attrib))
                if root.attrib['success'] == '0':
                    main.reply(sender, "Мне кажется, что Вы отправили пустую аудио-запись")
                else:
                    for child in root:
                        logging.info(str(child.tag) + " | " + str(child.attrib) + " | " + child.text)
                    resp = client.message(root[0].text)
                    logging.info('Yay, got Wit.ai response: ' + str(resp))
                    if not handle_entities(sender, last_sender_message, resp):
                        main.reply(sender, "Извините, я не уверена, что именно Вы хотите")
        except:
            logging.error(helper.PrintException())

        main.reply_typing_off(sender)
        try:
            os.remove(voice_filename)
            os.remove(voice_filename_wav)
        except:
            pass
    except:
        logging.error(helper.PrintException())

def handle_entities(sender, last_sender_message, resp):
    entities = resp['entities']
    if 'intent' in entities:
        for i in entities['intent']:
            if i['confidence'] > 0.5:
                handle_intent(sender, last_sender_message, i['value'])
                return True
    return False

def handle_intent(sender, last_sender_message, value):
    try:
        if value == 'greeting':
            message = "Здравствуйте, " + last_sender_message['first_name'] + "!\n"
            message += "Меня зовут Е-Сау+ле, я голосовая помощница этого бота."
            main.reply_just_text(sender, message.replace('+', ''))
            main.send_voice(sender, message)
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
            main.reply_main_menu_buttons(sender, last_sender_message)
        elif value == 'COMMAND_card2card':
            card2card.reply_card2card_enter_cardDst(sender, last_sender_message)
        elif value == 'COMMAND_paymobile':
            mobile.reply_mobile_enter_number(sender, last_sender_message)
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
        elif value == 'COMMAND_track':
            tracking.reply_tracking_enter_number(sender, last_sender_message)
        elif value == 'penalties_pdd' or value == 'COMMAND_penalties':
            shtrafy.reply_pdd_shtrafy(sender)
        elif value == 'info_post':
            tracking.reply_tracking_enter_number(sender, last_sender_message)
        elif value == 'how_are_you':
            main.reply(sender, "У меня всё замечательно!")
        elif value == 'FUN_anekdot':
            r = feedparser.parse('http://anekdotme.ru/RSS')
            random_int = randint(0, len(r['entries']) - 1)
            anekdot = r['entries'][random_int]['summary_detail']['value']
            anekdot = anekdot.replace('<br />', '\n').replace('&mdash;', '').replace('<BR>', '').replace('<br>', '')
            logging.info("Anekdot = " + anekdot)
            main.reply(sender, anekdot)
        elif value == 'thanx':
            main.reply(sender, "Всегда рада Вам служить, " + last_sender_message['first_name'] + "!")
        else:
            main.reply(sender, "Я не поняла Вашу команду")
    except:
        logging.error(helper.PrintException())

def handle_voice_message(sender, voice_url, last_sender_message):
    logging.info("Handling audio")
    try:
        main.reply_typing_on(sender)
        start = time.time()
        g = requests.get(voice_url, stream=True)
        logging.info('requests.get(voice_url) time = ' + str(time.time() - start))
        voice_filename = "voice_" + sender + ".mp4"
        #voice_filename_mp3 = "voice_" + sender + ".mp3"
        voice_filename_wav = "voice_" + sender + ".wav"
        with open(voice_filename, "wb") as o:
            start = time.time()
            o.write(g.content)
            logging.info('o.write(g.content) time = ' + str(time.time() - start))
        start = time.time()
        #AudioSegment.from_file(voice_filename, "mp4").export(voice_filename_mp3, format="mp3")
        AudioSegment.from_file(voice_filename, "mp4").export(voice_filename_wav, format="wav")
        logging.info('AudioSegment export time = ' + str(time.time() - start))
        with open(voice_filename_wav, 'rb') as f:
            try:
                start = time.time()
                resp = client.speech(f, None, {'Content-Type': 'audio/wav'})
                if "_text" in resp:
                    main.reply(sender, resp['_text'])
                logging.info('Wit.ai client.speech response time = ' + str(time.time() - start))
                logging.info('Yay, got Wit.ai response: ' + str(resp))
                handle_entities(sender, last_sender_message, resp)
            except:
                logging.info(helper.PrintException())
                main.reply(sender, "Извините, я не поняла что Вы сказали")
        main.reply_typing_off(sender)
        try:
            os.remove(voice_filename)
            #os.remove(voice_filename_mp3)
            os.remove(voice_filename_wav)
        except:
            pass
    except:
        logging.error(helper.PrintException())
