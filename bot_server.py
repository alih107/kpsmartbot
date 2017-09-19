import main
import voice_assistant
from flask import Flask, request
import requests
import pymongo
import constants
import logging
import datetime
import threading
import sys

app = Flask(__name__)
client = pymongo.MongoClient()
db = client.kpsmartbot_db
collection_messages = db.messages
logging.basicConfig(filename='botserver.log',level=logging.INFO,format='[%(levelname)s] (%(threadName)-10s) %(message)s')

ACCESS_TOKEN = constants.ACCESS_TOKEN

gosnomer_text = """Введите номер авто и номер техпаспорта через пробел
Правильный формат запроса: [номер авто] [номер техпаспорта]
Пример: 123AAA01 AA00000000"""

hint_main_menu = "(для перехода в главное меню нажмите кнопку (y)"
mobile_codes = ['tele2Wf', 'beelineWf', 'activWf', 'kcellWf']
digits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30']


@app.route('/kpsmartbot', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == "test_token":
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200

def print_facebook_data(data, last_sender_message):
    sender = data['entry'][0]['messaging'][0]['sender']['id']
    res = 'Sender id = ' + sender + ' | '

    try:
        last_sender_message = collection_messages.find_one({"sender": sender})
        assert last_sender_message != None
        res += 'Name = ' + last_sender_message['first_name'] + ' ' + last_sender_message['last_name'] + ' | '
    except:
        firstname, lastname = get_firstname_lastname(sender)
        res += '[new user] Name = ' + firstname + ' ' + lastname + ' | '

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

def reply(user_id, msg):
    data = {
        "recipient": {"id": user_id},
        "message": {"text": msg}
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data)

def get_firstname_lastname(user_id):
    call_string = "https://graph.facebook.com/v2.6/" + user_id + "?fields=first_name,last_name&access_token=" + ACCESS_TOKEN
    resp = requests.get(call_string).json()
    fn = resp["first_name"]
    ln = resp["last_name"]
    return fn, ln

@app.route('/kpsmartbot', methods=['POST'])
def handle_incoming_messages():
    data = request.json
    sender = data['entry'][0]['messaging'][0]['sender']['id']
    last_sender_message = collection_messages.find_one({"sender": sender})
    isIntroSent = False
    if last_sender_message == None:
        firstname, lastname = get_firstname_lastname(sender)
        db_record = {"sender": sender, "first_name": firstname, "last_name": lastname,
                     "isBotActive": True, 'phonesToRefill': []}
        last_sender_message = collection_messages.insert_one(db_record)
        reply_intro(sender)
        isIntroSent = True

    logging.info(print_facebook_data(data, last_sender_message))
    #logging.info(data)
    if not 'isBotActive' in last_sender_message:
        last_sender_message['isBotActive'] = True

    if not last_sender_message['isBotActive']:
        handle_messages_when_deactivated(sender, data, last_sender_message)
        return "ok"

    res = handle_sticker(sender, data, last_sender_message)
    if res == 'try next':
        res = handle_quickreply_payload(sender, data, last_sender_message)
    if res == 'try next':
        res = handle_postback_payload(sender, data, last_sender_message, isIntroSent)
    if res == 'try next':
        res = handle_attachments(sender, data, last_sender_message)
    if res == 'try next':
        res = handle_text_messages(sender, data, last_sender_message)

    return "ok"

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
        reply(sender, "Требуется авторизация, пожалуйста, отправьте логин и пароль профиля на post.kz через пробел. Если у вас нет аккаунта, то зарегистрируйтесь в https://post.kz/register")
        last_sender_message['payload'] = 'auth'
        collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)
        return False

    hasCards = main.reply_has_cards(sender, last_sender_message)
    if not hasCards:
        reply(sender, "Добавьте карту в профиль "+ last_sender_message['login'] +" на post.kz в разделе \"Мои счета и карты\", пожалуйста")
        main.reply_main_menu_buttons(sender)
        last_sender_message['payload'] = 'mainMenu'
        collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)
        return False

    return True

def check_login(sender, last_sender_message):
    try:
        encodedLoginPass = last_sender_message['encodedLoginPass']
        assert encodedLoginPass != None
        session = requests.Session()
        headers = {"Authorization": "Basic " + encodedLoginPass, 'Content-Type': 'application/json'}
        url_login = 'https://post.kz/mail-app/api/account/'
        r = session.get(url_login, headers=headers)
        assert r.status_code != 401
        return True
    except:
        reply(sender, "Требуется авторизация, пожалуйста, отправьте логин и пароль профиля на post.kz через пробел. Если у вас нет аккаунта, то зарегистрируйтесь в https://post.kz/register")
        last_sender_message['payload'] = 'auth'
        collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)
        return False

def reply_intro(sender):
    fn, ln = get_firstname_lastname(sender)
    result = "Добро пожаловать в бот АО КазПочта, " + ln + " " + fn + "!\n"
    result += "Это небольшое видео о том, как пользоваться ботом.\n"
    result += "Чтобы открыть главное меню, нажмите (y)"
    main.reply_gif_desktop(sender)
    main.reply_gif_mobile(sender)
    reply(sender, result)

def handle_quickreply_payload(sender, data, last_sender_message):
    try:
        payload = data['entry'][0]['messaging'][0]['message']['quick_reply']['payload']
        text = data['entry'][0]['messaging'][0]['message']['text']
        if payload == '4.IIN':
            reply(sender, "Введите 12-ти значный ИИН\n" + hint_main_menu)
        elif payload == '4.GosNomer':
            reply(sender, gosnomer_text + "\n" + hint_main_menu)
        elif payload == 'tracking.last':
            main.reply_tracking(sender, text, last_sender_message)
            payload = 'tracking'
        elif payload == 'onai.last':
            main.reply_onai(sender, text, last_sender_message)
            payload = 'onai.amount'
        elif payload == 'mobile.last':
            main.reply_check_mobile_number(sender, text, last_sender_message)
            return "ok"
        elif payload == 'mobile.delete':
            main.reply_mobile_delete(sender, last_sender_message)
            return "ok"
        elif payload == 'mobile.delete.phone':
            main.reply_mobile_delete_phone(sender, text, last_sender_message)
            return "ok"
        elif payload == 'card2card.last':
            main.reply_card2card_check_cardDst(sender, text, last_sender_message)
            payload = 'card2card.amount'
        elif payload == 'auth.delete.yes':
            last_sender_message['encodedLoginPass'] = None
            reply(sender, "Авторизация успешна удалена")
            main.reply_main_menu_buttons(sender)
        elif payload == 'auth.delete.no':
            main.reply_main_menu_buttons(sender)
        last_sender_message['payload'] = payload
        collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)
        return "ok"

    except:
        return "try next"

# кнопки главного меню
def handle_postback_payload(sender, data, last_sender_message, isIntroSent):
    try:
        payload = data['entry'][0]['messaging'][0]['postback']['payload']
        if payload == 'GET_STARTED_PAYLOAD':
            if not isIntroSent:
                reply_intro(sender)
            return "ok"
        if payload == 'reroute':
            reply(sender, "[не работает] Введите трек-номер посылки\n" + hint_main_menu)
        elif payload == 'tracking':
            call_tracking(sender, last_sender_message, payload)
        elif payload == 'extension':
            reply(sender, "[не работает] Введите трек-номер посылки\n" + hint_main_menu)
        elif payload == 'shtrafy':
            main.reply_pdd_shtrafy(sender)
        elif payload == 'komuslugi':
            main.reply_komuslugi_cities(sender)
        elif payload == 'nearest':
            main.reply_nearest(sender)
        elif payload == 'nearest.postamats' or payload == 'nearest.offices' or payload == 'nearest.atms':
            call_request_nearest_location(sender, last_sender_message, payload)
            return "ok"
        elif payload == 'balance':
            if not call_balance(sender, last_sender_message, payload):
                return "ok"
        elif payload == 'card2card':
            if not call_card2card(sender, last_sender_message, payload):
                return "ok"
        elif payload == 'card2cash':
            reply(sender, "[не работает] Введите номер карты отправителя в формате\n0000 0000 0000 0000\n" + hint_main_menu)
        elif payload == 'courier':
            reply(sender, "[не работает] Отправьте геолокацию\n" + hint_main_menu)
        elif payload == 'currencies':
            main.reply_currencies(sender)
        elif payload == '10.kursy':
            main.reply_currencies_kursy(sender)
        elif payload == '10.grafik':
            main.reply_currencies_grafik(sender)
        elif payload == 'closest':
            main.reply_closest(sender)
        elif payload == 'misc':
            main.reply_misc(sender)
        elif payload == 'onai':
            if not call_onai(sender, last_sender_message, payload):
                return "ok"
        elif payload == 'auth':
            try:
                encodedLoginPass = last_sender_message['encodedLoginPass']
                assert encodedLoginPass != None
                answer = "Вы уже авторизованы под логином " + last_sender_message['login']+ ".\n"
                answer += "Вы можете переотправить логин и пароль профиля на post.kz через пробел для новой авторизации\n"
                answer += hint_main_menu
                reply(sender, answer)
            except:
                reply(sender, "Для авторизации отправьте логин и пароль профиля на post.kz через пробел. Если у вас нет аккаунта то зарегистрируйтесь в https://post.kz/register")

        elif payload in digits:
            last_sender_message['chosenCardIndex'] = int(payload)
            lastCommand = last_sender_message['lastCommand']
            if lastCommand == 'balance':
                main.reply_mobile_csc(sender, payload, last_sender_message)
                payload = 'mobile.startPayment'
            elif lastCommand == 'onai':
                main.reply_onai_csc(sender, payload, last_sender_message)
                payload = 'onai.startPayment'
            elif lastCommand == 'card2card':
                main.reply_card2card_csc(sender, payload, last_sender_message)
                payload = 'card2card.startPayment'
        elif payload == 'auth.delete':
            try:
                res = last_sender_message['encodedLoginPass']
                assert res != None
                main.reply_auth_delete(sender)
            except:
                reply(sender, "Авторизации нет")
        elif payload == 'addcard':
            if not call_addcard(sender, last_sender_message, payload):
                return "ok"
        elif payload == 'send.message':
            call_sendmessage(sender, last_sender_message, payload)
            return "ok"
        else:
            logging.info("Ne raspoznana komanda")

        last_sender_message['payload'] = payload
        collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
        return "ok"

    except:
        return "try next"

def handle_attachments(sender, data, last_sender_message):
    try:
        attachment = data['entry'][0]['messaging'][0]['message']['attachments'][0]
        type = attachment['type']
        payload = last_sender_message['payload']
        if type == 'location':
            if payload == 'nearest.postamats' or payload == 'nearest.offices' or payload == 'nearest.atms':
                coordinates = attachment['payload']['coordinates']
                locLong = coordinates['long']
                locLat = coordinates['lat']
                main.reply_nearest_find(sender, locLong, locLat, payload)
            else:
                reply(sender, "А для чего Вы мне отправили своё местоположение?")
        if type == 'audio':
            t = threading.Thread(target=voice_assistant.handle_voice_message,
                                 args=(sender, attachment['payload']['url'], last_sender_message,))
            t.setDaemon(True)
            t.start()
    except:
        return "try next"

def handle_text_messages(sender, data, last_sender_message):
    try:
        message = data['entry'][0]['messaging'][0]['message']['text']
        payload = last_sender_message['payload']
        if payload == 'tracking':
            main.reply_tracking(sender, message, last_sender_message)
            return "ok"
        elif payload == '4.IIN':
            main.reply_pdd_shtrafy_iin(sender, message, last_sender_message)
            return "ok"
        elif payload == '4.GosNomer':
            main.reply_pdd_shtrafy_gosnomer(sender, message, last_sender_message)
            return "ok"
        elif payload == 'auth':
            main.reply_auth(sender, message, last_sender_message)
            return "ok"
        elif payload == 'balance':
            main.reply_check_mobile_number(sender, message, last_sender_message)
            return "ok"
        elif payload == 'card2card':
            main.reply_card2card_check_cardDst(sender, message, last_sender_message)
            return "ok"
        elif payload == 'card2card.amount':
            main.reply_card2card_amount(sender, message, last_sender_message)
            return "ok"
        elif payload == 'card2card.chooseCard':
            main.reply_display_cards(sender, last_sender_message)
            return "ok"
        elif payload == 'mobile.amount':
            main.reply_mobile_amount(sender, message, last_sender_message)
            return "ok"
        elif payload == 'mobile.chooseCard':
            main.reply_display_cards(sender, last_sender_message)
            return "ok"
        elif payload == 'mobile.startPayment':
            t = threading.Thread(target=main.reply_mobile_startPayment, args=(sender, message, last_sender_message,))
            t.setDaemon(True)
            t.start()
            logging.info('main.reply_mobile_startPayment called with a new thread')
            return "ok"
        elif payload == 'mobile.finished' or payload == 'onai.finished':
            return "ok"
        elif payload == 'onai':
            main.reply_onai(sender, message, last_sender_message)
            return "ok"
        elif payload == 'onai.amount':
            main.reply_onai_amount(sender, message, last_sender_message)
            return "ok"
        elif payload == 'onai.startPayment':
            t = threading.Thread(target=main.reply_onai_startPayment, args=(sender, message, last_sender_message,))
            t.setDaemon(True)
            t.start()
            logging.info('main.reply_onai_startPayment called with a new thread')
            return "ok"
        elif payload == 'card2card.startPayment':
            t = threading.Thread(target=main.reply_card2card_startPayment, args=(sender, message, last_sender_message,))
            t.setDaemon(True)
            t.start()
            logging.info('main.reply_card2card_startPayment called with a new thread')
            return "ok"
        elif payload == 'addcard':
            main.reply_addcard_checkcard(sender, message, last_sender_message)
            return "ok"
        elif payload == 'addcard.expiredate':
            main.reply_addcard_checkexpiredate(sender, message, last_sender_message)
            return "ok"
        elif payload == 'addcard.cardowner':
            main.reply_addcard_checkcardowner(sender, message, last_sender_message)
            return "ok"
        elif payload == 'addcard.confirmation':
            main.card_registration_confirm(sender, message, last_sender_message)
            return "ok"
        elif payload == 'addcard.csc':
            t = threading.Thread(target=main.reply_addcard_startAdding, args=(sender, message, last_sender_message,))
            t.setDaemon(True)
            t.start()
            logging.info('main.reply_addcard_startAdding called with a new thread')
            return "ok"
        elif payload == 'send.message':
            res = "Спасибо, Ваше сообщение принято! Ожидайте ответа от операторов\n"
            res += "Сейчас бот отключен. Чтобы включить, нажмите кнопку (y)"
            last_sender_message['isBotActive'] = False
            reply(sender, res)
            return "ok"
        main.reply_main_menu_buttons(sender)
        last_sender_message['payload'] = 'mainMenu'
        collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
        return "ok"

    except:
        return "try next"

def handle_sticker(sender, data, last_sender_message):
    try:
        sticker_id = data['entry'][0]['messaging'][0]['message']['sticker_id']
        last_sender_message['payload'] = 'mainMenu'
        collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
        main.reply_main_menu_buttons(sender)
        return "ok"
    except:
        return "try next"

def handle_messages_when_deactivated(sender, data, last_sender_message):
    try:
        sticker_id = data['entry'][0]['messaging'][0]['message']['sticker_id']
        data_quick_replies = {
            "recipient": {
                "id": sender
            },
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
        resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN,
                             json=data_quick_replies)
        return
    except:
        pass

    try:
        payload = data['entry'][0]['messaging'][0]['message']['quick_reply']['payload']
        if payload == 'activate.bot':
            last_sender_message['isBotActive'] = True
            collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)
            reply(sender, "Бот включен")
            main.reply_main_menu_buttons(sender)
        if payload == 'deactivate.bot':
            reply(sender, "Хорошо! Если Вы хотите включить бота, нажмите кнопку (y)")
    except:
        return

def call_card2card(sender, last_sender_message, payload):
    if check_login_and_cards(sender, last_sender_message):
        last_sender_message['lastCommand'] = payload
        main.reply_card2card_enter_cardDst(sender, last_sender_message)
        return True
    return False

def call_balance(sender, last_sender_message, payload):
    if check_login_and_cards(sender, last_sender_message):
        last_sender_message['lastCommand'] = payload
        main.reply_mobile_enter_number(sender, last_sender_message)
        return True
    return False

def call_onai(sender, last_sender_message, payload):
    if check_login_and_cards(sender, last_sender_message):
        last_sender_message['lastCommand'] = payload
        main.reply_onai_enter_number(sender, last_sender_message)
        return True
    return False

def call_sendmessage(sender, last_sender_message, payload):
    reply(sender, "Пожалуйста, отправьте сообщение, которое Вас интересует")
    last_sender_message['payload'] = payload
    collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)

def call_tracking(sender, last_sender_message, payload):
    try:
        lastTrackingNumber = last_sender_message['lastTrackingNumber']
        data_quick_replies = {
            "recipient": {
                "id": sender
            },
            "message": {
                "text": "Выберите последний трекинг-номер или введите его\n" + hint_main_menu,
                "quick_replies": [
                    {
                        "content_type": "text",
                        "title": lastTrackingNumber,
                        "payload": "tracking.last"
                    }
                ]
            }
        }
        resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN,
                             json=data_quick_replies)
    except:
        reply(sender, "Введите трек-номер посылки\n" + hint_main_menu)
    last_sender_message['payload'] = payload
    collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)

def call_addcard(sender, last_sender_message, payload):
    if check_login(sender, last_sender_message):
        main.reply_addcard_entercard(sender, last_sender_message)
        return True
    return False

def call_request_nearest_location(sender, last_sender_message, payload):
    main.reply_nearest_request_location(sender, payload)
    last_sender_message['payload'] = payload
    collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)

if __name__ == '__main__':
	app.run(debug=True)
