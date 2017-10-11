from flask import Flask, request
import requests
import pymongo
import logging
import datetime
import threading

import main
import komuslugi
import helper
import voice_assistant
from finances import mobile
from finances import onai
from finances import card2card
from finances import card2cash
from finances import addcard
from services import shtrafy
from services import tracking

app = Flask(__name__)
client = pymongo.MongoClient()
db = client.kpsmartbot_db
collection_messages = db.messages
logging.basicConfig(filename='botserver.log', level=logging.INFO,
                    format='[%(levelname)s] (%(threadName)-10s) %(message)s')

ACCESS_TOKEN = main.ACCESS_TOKEN
fb_url = main.fb_url

hint_main_menu = "(для перехода в главное меню нажмите кнопку (y)"
digits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15',
          '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30']


@app.route('/kpsmartbot', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == "test_token":
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Wake up, Neo... The Matrix has you", 200

def print_facebook_data(data, sender, last_sender_message):
    res = 'Sender id = ' + sender + ' | '
    res += 'Name = ' + last_sender_message['first_name'] + ' ' + last_sender_message['last_name'] + ' | '
    ms = int(data['entry'][0]['time']) / 1000.0
    ms1 = int(data['entry'][0]['messaging'][0]['timestamp']) / 1000.0
    tdiff = round(ms - ms1, 2)
    strtimestamp = datetime.datetime.fromtimestamp(ms1).strftime('%Y-%m-%d %H:%M:%S')
    res += 'Timestamp = ' + strtimestamp + ', tdiff = ' + str(tdiff) + ' | '
    try:
        sticker_id = data['entry'][0]['messaging'][0]['message']['sticker_id']
        res += 'Received sticker' + ' | '
    except:
        pass

    try:
        attachment = data['entry'][0]['messaging'][0]['message']['attachments'][0]
        type = attachment['type']
        if type == 'location':
            coordinates = attachment['payload']['coordinates']
            locLong = coordinates['long']
            locLat = coordinates['lat']
            latCommaLong = str(locLat) + ',' + str(locLong)
            res += 'Received location = ' + latCommaLong + '; payload = ' + last_sender_message['payload']
        if type == 'audio':
            res += 'Received audio'
    except:
        pass

    try:
        payload = data['entry'][0]['messaging'][0]['message']['quick_reply']['payload']
        text = data['entry'][0]['messaging'][0]['message']['text']
        res += 'Received quick-reply, payload = ' + payload + ', text = ' + text + ' | '
    except:
        pass

    try:
        payload = data['entry'][0]['messaging'][0]['postback']['payload']
        res += 'Received postback, payload = ' + payload

    except:
        pass

    try:
        message = data['entry'][0]['messaging'][0]['message']['text']
        res += 'Received message = ' + message
        try:
            res += ', payload = ' + last_sender_message['payload']
        except:
            pass
    except:
        pass

    return res

def get_firstname_lastname(sender):
    call_string = "https://graph.facebook.com/v2.6/" + sender + \
                  "?fields=first_name,last_name&access_token=" + ACCESS_TOKEN
    resp = requests.get(call_string).json()
    return resp["first_name"], resp["last_name"]

@app.route('/kpsmartbot', methods=['POST'])
def handle_incoming_messages():
    data = request.json
    t = threading.Thread(target=handle_data, args=(data,))
    t.setDaemon(True)
    t.start()

    return "ok", 200

def handle_data(data):
    sender = data['entry'][0]['messaging'][0]['sender']['id']
    last_sender_message = collection_messages.find_one({"sender": sender})
    if last_sender_message == None:
        fn, ln = get_firstname_lastname(sender)
        db_record = {"sender": sender, "first_name": fn, "last_name": ln, "isBotActive": True, 'phonesToRefill': [],
                     'onaisToRefill': [], 'trackingNumbers': [], 'pddIINs': [], 'pddGosnomers': [], 'cardDsts': [],
                     'hasCards': False, 'encodedLoginPass': None, 'payload': 'mainMenu'}
        last_sender_message = collection_messages.insert_one(db_record)
        reply_intro(sender)
        logging.info("We've got new user! Sender = " + sender + " | " + fn + " " + ln)
        return "ok"

    logging.info(print_facebook_data(data, sender, last_sender_message))
    last_sender_message['sendVoice'] = False
    main.mongo_update_record(last_sender_message)
    if not last_sender_message['isBotActive']:
        handle_messages_when_deactivated(sender, data, last_sender_message)
        return "ok"

    try:
        sticker_id = data['entry'][0]['messaging'][0]['message']['sticker_id']
        handle_sticker(sender, last_sender_message)
        return "ok"
    except:
        pass

    try:
        payload = data['entry'][0]['messaging'][0]['message']['quick_reply']['payload']
        handle_quickreply_payload(sender, data, last_sender_message, payload)
        return "ok"
    except:
        pass

    try:
        payload = data['entry'][0]['messaging'][0]['postback']['payload']
        handle_postback_payload(sender, last_sender_message, payload)
        return "ok"
    except:
        pass

    try:
        attachment = data['entry'][0]['messaging'][0]['message']['attachments'][0]
        handle_attachments(sender, last_sender_message, attachment)
        return "ok"
    except:
        pass

    try:
        message = data['entry'][0]['messaging'][0]['message']['text']
        handle_text_messages(sender, last_sender_message, message)
        return "ok"
    except:
        pass

def check_login_and_cards(sender, last_sender_message):
    try:
        encodedLoginPass = last_sender_message['encodedLoginPass']
        assert encodedLoginPass != None
        session = requests.Session()
        headers = {"Authorization": "Basic " + encodedLoginPass, 'Content-Type': 'application/json'}
        url_login = 'https://post.kz/mail-app/api/account/'
        r = session.get(url_login, headers=headers)
        assert r.status_code != 401
    except:
        main.reply(sender, "Требуется авторизация, пожалуйста, отправьте логин и пароль профиля на post.kz через "
                           "пробел. Если у вас нет аккаунта, то зарегистрируйтесь в https://post.kz/register")
        last_sender_message['payload'] = 'auth'
        main.mongo_update_record(last_sender_message)
        return False

    hasCards = main.reply_has_cards(sender, last_sender_message)
    if not hasCards:
        main.reply(sender, "У вас отсутствуют добавленные карты в post.kz. "
                      "Чтобы добавить, введите 16ти-значный номер карты")
        last_sender_message['payload'] = 'addcard'
        main.mongo_update_record(last_sender_message)
        return False

    return True

def reply_intro(sender):
    fn, ln = get_firstname_lastname(sender)
    result = "Добро пожаловать в бот АО КазПочта, " + ln + " " + fn + "!\n"
    result += "Это небольшое видео о том, как пользоваться ботом.\n"
    result += "Чтобы открыть главное меню, нажмите (y)"
    main.reply_gif_desktop(sender)
    main.reply_gif_mobile(sender)
    main.reply(sender, result)

def handle_quickreply_payload(sender, data, last_sender_message, payload):
    text = data['entry'][0]['messaging'][0]['message']['text']
    if payload == '4.IIN':
        shtrafy.reply_pdd_shtrafy_iin_enter(sender, last_sender_message)
        return "ok"
    if payload == 'pddIIN.last':
        shtrafy.reply_pdd_shtrafy_iin(sender, text, last_sender_message)
        return "ok"
    if payload == 'pddIIN.delete':
        shtrafy.reply_pdd_shtrafy_iin_delete(sender, last_sender_message)
        return "ok"
    if payload == 'pddIIN.delete.number':
        shtrafy.reply_pdd_shtrafy_iin_delete_iin(sender, text, last_sender_message)
        return "ok"
    elif payload == '4.GosNomer':
        shtrafy.reply_pdd_shtrafy_gosnomer_enter(sender, last_sender_message)
        return "ok"
    elif payload == 'pddGosnomer.last':
        shtrafy.reply_pdd_shtrafy_gosnomer(sender, text, last_sender_message)
        return "ok"
    elif payload == 'pddGosnomer.delete':
        shtrafy.reply_pdd_shtrafy_gosnomer_delete(sender, last_sender_message)
        return "ok"
    elif payload == 'pddGosnomer.delete.number':
        shtrafy.reply_pdd_shtrafy_gosnomer_delete_gosnomer(sender, text, last_sender_message)
        return "ok"
    elif payload == 'astanaErc.last':
        komuslugi.reply_astanaErc(sender, text, last_sender_message)
        return "ok"
    elif payload == 'astanaErc.delete':
        komuslugi.reply_astanaErc_delete(sender, last_sender_message)
        return "ok"
    elif payload == 'astanaErc.delete.acc':
        komuslugi.reply_astanaErc_delete_acc(sender, text, last_sender_message)
        return "ok"
    elif payload == 'astanaErc.pay':
        komuslugi.reply_astanaErc_chooseCard(sender, last_sender_message)
        return "ok"
    elif payload == 'tracking.last':
        tracking.reply_tracking(sender, text, last_sender_message)
        payload = 'tracking'
    elif payload == 'tracking.delete':
        tracking.reply_tracking_delete(sender, last_sender_message)
    elif payload == 'tracking.delete.number':
        tracking.reply_tracking_delete_number(sender, text, last_sender_message)
        payload = 'tracking'
    elif payload == 'onai.last':
        onai.reply_onai(sender, text, last_sender_message)
        payload = 'onai.amount'
    elif payload == 'onai.delete':
        onai.reply_onai_delete(sender, last_sender_message)
        return "ok"
    elif payload == 'onai.delete.phone':
        onai.reply_onai_delete_phone(sender, text, last_sender_message)
        return "ok"
    elif payload == 'mobile.last':
        mobile.reply_mobile_check_number(sender, text, last_sender_message)
        return "ok"
    elif payload == 'mobile.voice_number.again':
        mobile.reply_mobile_enter_number(sender, last_sender_message)
        return "ok"
    elif payload == 'mobile.delete':
        mobile.reply_mobile_delete(sender, last_sender_message)
        return "ok"
    elif payload == 'mobile.delete.phone':
        mobile.reply_mobile_delete_phone(sender, text, last_sender_message)
        return "ok"
    elif payload == 'card2card.last':
        card2card.reply_card2card_check_cardDst(sender, text, last_sender_message)
        payload = 'card2card.amount'
    elif payload == 'card2card.delete':
        card2card.reply_card2card_delete(sender, last_sender_message)
    elif payload == 'card2card.again':
        last_sender_message['cardDsts'].remove(last_sender_message['lastCardDst'])
        card2card.reply_card2card_enter_cardDst(sender, last_sender_message)
        return "ok"
    elif payload == 'card2card.delete.card':
        card2card.reply_card2card_delete_card(sender, text, last_sender_message)
        return "ok"
    elif payload == 'card2card.info':
        main.reply_just_text(sender, card2card.card2card_info)
        card2card.reply_card2card_enter_cardDst(sender, last_sender_message)
        return
    elif payload == 'auth.delete.yes':
        last_sender_message['encodedLoginPass'] = None
        main.reply(sender, "Авторизация успешна удалена")
        main.reply_main_menu_buttons(sender, last_sender_message)
        return
    elif payload == 'auth.delete.no':
        main.reply_main_menu_buttons(sender, last_sender_message)
    elif payload == 'disable.bot.yes':
        res = "Бот отключен. Чтобы включить, нажмите кнопку (y)"
        last_sender_message['isBotActive'] = False
        main.reply(sender, res)
    elif payload == 'disable.bot.no':
        main.reply(sender, "Бот остался включенным")
        main.reply_main_menu_buttons(sender, last_sender_message)
    last_sender_message['payload'] = payload
    main.mongo_update_record(last_sender_message)

# кнопки главного меню
def handle_postback_payload(sender, last_sender_message, payload):
    if last_sender_message['payload'] == 'card2cash':
        card2cash.reply_card2cash_history_show(sender, last_sender_message, payload)
        last_sender_message['payload'] = 'card2cash.show'
        main.mongo_update_record(last_sender_message)
        return "ok"

    if payload == 'GET_STARTED_PAYLOAD':
        reply_intro(sender)
        return "ok"
    elif payload == 'tracking':
        tracking.reply_tracking_enter_number(sender, last_sender_message)
        return "ok"
    elif payload == 'shtrafy':
        shtrafy.reply_pdd_shtrafy(sender)
    elif payload == 'komuslugi':
        komuslugi.reply_komuslugi_cities(sender)
    elif payload == 'astanaErc':
        komuslugi.reply_astanaErc_enter(sender, last_sender_message)
        return "ok"
    elif payload == 'nearest':
        main.reply_nearest(sender)
    elif payload == 'nearest.postamats' or payload == 'nearest.offices' or payload == 'nearest.atms':
        call_request_nearest_location(sender, last_sender_message, payload)
        return "ok"
    elif payload == 'balance':
        mobile.reply_mobile_enter_number(sender, last_sender_message)
        return "ok"
    elif payload == 'card2card':
        card2card.reply_card2card_enter_cardDst(sender, last_sender_message)
        return "ok"
    elif payload == 'card2cash':
        if not call_card2cash(sender, last_sender_message, payload):
            return "ok"
    elif payload == '10.kursy':
        main.reply_currencies_kursy(sender)
    elif payload == 'misc':
        main.reply_misc(sender)
    elif payload == 'onai':
        if not call_onai(sender, last_sender_message, payload):
            return "ok"
    elif payload == 'auth':
        try:
            encodedLoginPass = last_sender_message['encodedLoginPass']
            assert encodedLoginPass != None
            answer = "Вы уже авторизованы под логином " + last_sender_message['login'] + ".\n"
            answer += "Вы можете переотправить логин и пароль профиля на post.kz через пробел для новой авторизации\n"
            answer += hint_main_menu
            main.reply(sender, answer)
        except:
            main.reply(sender, "Для авторизации отправьте логин и пароль профиля на post.kz через пробел. "
                               "Если у вас нет аккаунта то зарегистрируйтесь в https://post.kz/register")

    elif payload in digits:
        last_sender_message['chosenCardIndex'] = int(payload)
        lastCommand = last_sender_message['lastCommand']
        if lastCommand == 'balance':
            mobile.reply_mobile_csc(sender, payload, last_sender_message)
            payload = 'mobile.startPayment'
        elif lastCommand == 'onai':
            onai.reply_onai_csc(sender, payload, last_sender_message)
            payload = 'onai.startPayment'
        elif lastCommand == 'card2card':
            card2card.reply_card2card_csc(sender, payload, last_sender_message)
            payload = 'card2card.startPayment'
        elif lastCommand == 'astanaErc':
            komuslugi.reply_astanaErc_csc(sender, payload, last_sender_message)
            payload = 'astanaErc.startPayment'
    elif payload == 'auth.delete':
        try:
            assert last_sender_message['encodedLoginPass'] != None
            main.reply_auth_delete(sender)
        except:
            main.reply(sender, "Авторизации нет")
    elif payload == 'addcard':
        if not call_addcard(sender, last_sender_message, payload):
            return "ok"
    elif payload == 'disable.bot':
        call_disable_bot(sender, last_sender_message, payload)
        return "ok"
    elif payload == 'send.message':
        call_sendmessage(sender, last_sender_message, payload)
        return "ok"
    else:
        logging.info("Ne raspoznana komanda")

    last_sender_message['payload'] = payload
    main.mongo_update_record(last_sender_message)

def handle_attachments(sender, last_sender_message, attachment):
    attachment_type = attachment['type']
    payload = last_sender_message['payload']
    if attachment_type == 'location':
        if payload == 'nearest.postamats' or payload == 'nearest.offices' or payload == 'nearest.atms':
            coordinates = attachment['payload']['coordinates']
            main.reply_nearest_find(sender, coordinates['long'], coordinates['lat'], payload)
        else:
            main.reply(sender, "А для чего Вы мне отправили своё местоположение?")
    if attachment_type == 'audio':
        last_sender_message['sendVoice'] = True
        main.mongo_update_record(last_sender_message)
        try:
            t = threading.Thread(target=voice_assistant.handle_voice_message_yandex,
                                 args=(sender, attachment['payload']['url'], last_sender_message,))
            t.setDaemon(True)
            t.start()
        except:
            logging.error(helper.PrintException())

def handle_text_messages(sender, last_sender_message, message):
    if message == '👍':
        main.reply_main_menu_buttons(sender, last_sender_message)
        return "ok"
    payload = last_sender_message['payload']
    if payload == 'tracking':
        tracking.reply_tracking(sender, message, last_sender_message)
        return "ok"
    elif payload == '4.IIN':
        shtrafy.reply_pdd_shtrafy_iin(sender, message, last_sender_message)
        return "ok"
    elif payload == '4.GosNomer':
        shtrafy.reply_pdd_shtrafy_gosnomer(sender, message, last_sender_message)
        return "ok"
    elif payload == 'astanaErc.enter':
        komuslugi.reply_astanaErc(sender, message, last_sender_message)
        return "ok"
    elif payload == 'astanaErc.startPayment':
        t = threading.Thread(target=komuslugi.reply_astanaErc_startPayment, args=(sender, message, last_sender_message,))
        t.setDaemon(True)
        t.start()
        return "ok"
    elif payload == 'auth':
        main.reply_auth(sender, message, last_sender_message)
        return "ok"
    elif payload == 'balance':
        mobile.reply_mobile_check_number(sender, message, last_sender_message)
        return "ok"
    elif payload == 'card2cash.show':
        card2cash.reply_card2cash_history_startPayment(sender, message, last_sender_message)
        return "ok"
    elif payload == 'card2card':
        card2card.reply_card2card_check_cardDst(sender, message, last_sender_message)
        return "ok"
    elif payload == 'card2card.amount':
        card2card.reply_card2card_amount(sender, message, last_sender_message)
        return "ok"
    elif payload == 'card2card.chooseCard':
        main.reply_display_cards(sender, last_sender_message)
        return "ok"
    elif payload == 'mobile.amount':
        mobile.reply_mobile_amount(sender, message, last_sender_message)
        return "ok"
    elif payload == 'mobile.chooseCard':
        main.reply_display_cards(sender, last_sender_message)
        return "ok"
    elif payload == 'mobile.startPayment':
        t = threading.Thread(target=mobile.reply_mobile_startPayment, args=(sender, message, last_sender_message,))
        t.setDaemon(True)
        t.start()
        return "ok"
    elif payload == 'mobile.finished' or payload == 'onai.finished':
        return "ok"
    elif payload == 'onai':
        onai.reply_onai(sender, message, last_sender_message)
        return "ok"
    elif payload == 'onai.amount':
        onai.reply_onai_amount(sender, message, last_sender_message)
        return "ok"
    elif payload == 'onai.startPayment':
        t = threading.Thread(target=onai.reply_onai_startPayment, args=(sender, message, last_sender_message,))
        t.setDaemon(True)
        t.start()
        return "ok"
    elif payload == 'card2card.startPayment':
        t = threading.Thread(target=card2card.reply_card2card_startPayment, args=(sender, message, last_sender_message,))
        t.setDaemon(True)
        t.start()
        return "ok"
    elif payload == 'addcard':
        addcard.reply_addcard_checkcard(sender, message, last_sender_message)
        return "ok"
    elif payload == 'addcard.expiredate':
        addcard.reply_addcard_checkexpiredate(sender, message, last_sender_message)
        return "ok"
    elif payload == 'addcard.cardowner':
        addcard.reply_addcard_checkcardowner(sender, message, last_sender_message)
        return "ok"
    elif payload == 'addcard.confirmation':
        addcard.card_registration_confirm(sender, message, last_sender_message)
        return "ok"
    elif payload == 'addcard.csc':
        t = threading.Thread(target=addcard.reply_addcard_startAdding, args=(sender, message, last_sender_message,))
        t.setDaemon(True)
        t.start()
        return "ok"
    elif payload == 'astanaErc.startPayment':
        t = threading.Thread(target=komuslugi.reply_astanaErc_startPayment, args=(sender, message, last_sender_message,))
        t.setDaemon(True)
        t.start()
        return "ok"
    elif payload == 'send.message':
        res = "Спасибо, Ваше сообщение принято! Ожидайте ответа от операторов\n"
        res += "Сейчас бот отключен. Чтобы включить, нажмите кнопку (y)"
        last_sender_message['isBotActive'] = False
        main.reply(sender, res)
        return "ok"
    main.reply_main_menu_buttons(sender, last_sender_message)

def handle_sticker(sender, last_sender_message):
    main.reply_main_menu_buttons(sender, last_sender_message)

def handle_messages_when_deactivated(sender, data, last_sender_message):
    try:
        sticker_id = data['entry'][0]['messaging'][0]['message']['sticker_id']
        data_quick_replies = {
            "recipient": {"id": sender},
            "message": {
                "text": "Вы хотите включить бота?",
                "quick_replies": [
                    {
                        "content_type": "text",
                        "title": "Да, включить бота",
                        "payload": "activate.bot"
                    },
                    {
                        "content_type": "text",
                        "title": "Нет",
                        "payload": "deactivate.bot"
                    }
                ]
            }
        }
        requests.post(fb_url, json=data_quick_replies)
        return
    except:
        pass

    try:
        payload = data['entry'][0]['messaging'][0]['message']['quick_reply']['payload']
        if payload == 'activate.bot':
            last_sender_message['isBotActive'] = True
            main.mongo_update_record(last_sender_message)
            main.reply(sender, "Бот включен")
            main.reply_main_menu_buttons(sender, last_sender_message)
        if payload == 'deactivate.bot':
            main.reply(sender, "Хорошо! Если Вы хотите включить бота, нажмите кнопку (y)")
    except:
        return

def call_card2cash(sender, last_sender_message, payload):
    if main.check_login(sender, last_sender_message):
        last_sender_message['lastCommand'] = payload
        card2cash.reply_card2cash_history(sender, last_sender_message)
        return True
    return False

def call_onai(sender, last_sender_message, payload):
    if main.check_login(sender, last_sender_message):
        last_sender_message['lastCommand'] = payload
        onai.reply_onai_enter_number(sender, last_sender_message)
        return True
    return False

def call_sendmessage(sender, last_sender_message, payload):
    main.reply(sender, "Пожалуйста, отправьте сообщение, которое Вас интересует")
    last_sender_message['payload'] = payload
    main.mongo_update_record(last_sender_message)

def call_disable_bot(sender, last_sender_message, payload):
    data_quick_replies = {
        "recipient": {"id": sender},
        "message": {
            "text": "Вы хотите отключить бота?",
            "quick_replies": [
                {
                    "content_type": "text",
                    "title": "Да, отключить бота",
                    "payload": "disable.bot.yes"
                },
                {
                    "content_type": "text",
                    "title": "Нет",
                    "payload": "disable.bot.no"
                }
            ]
        }
    }
    requests.post(fb_url, json=data_quick_replies)
    last_sender_message['payload'] = payload
    main.mongo_update_record(last_sender_message)

def call_addcard(sender, last_sender_message, payload):
    if main.check_login(sender, last_sender_message):
        addcard.reply_addcard_entercard(sender, last_sender_message)
        last_sender_message['payload'] = payload
        main.mongo_update_record(last_sender_message)
        return True
    return False

def call_request_nearest_location(sender, last_sender_message, payload):
    main.reply_nearest_request_location(sender, payload)
    last_sender_message['payload'] = payload
    main.mongo_update_record(last_sender_message)

if __name__ == '__main__':
    app.run(debug=True)
