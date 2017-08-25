import sys
import main
from flask import Flask, request
import requests
import pymongo
import constants

app = Flask(__name__)
client = pymongo.MongoClient()
db = client.kpsmartbot_db
collection_messages = db.messages

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
    logging.info ("#############RECEIVED MESSAGE###############################")
    logging.info (data)
    sender = data['entry'][0]['messaging'][0]['sender']['id']
    last_sender_message = collection_messages.find_one({"sender": sender})
    if last_sender_message == None:
        firstname, lastname = get_firstname_lastname(sender)
        db_record = {"sender":sender, "first_name":firstname, "last_name":lastname}
        last_sender_message = collection_messages.insert_one(db_record)
    #print ("###### what is received #########")
    #print (data)
    try:
        sticker_id = data['entry'][0]['messaging'][0]['message']['sticker_id']
        last_sender_message['payload'] = 'mainMenu'
        collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
        main.reply_main_menu_buttons(sender)
        return "ok"    
    except:
        logging.info ("No sticker")

    try:
        payload = data['entry'][0]['messaging'][0]['message']['quick_reply']['payload']
        if payload == '4.IIN':
            reply(sender, "Введите 12-ти значный ИИН\n" + hint_main_menu)  
        elif payload == '4.GosNomer':
            reply(sender, gosnomer_text + "\n" + hint_main_menu)
        elif payload == 'onai.last':
            main.reply_onai(sender, data['entry'][0]['messaging'][0]['message']['text'], last_sender_message)
            payload = 'onai.amount'
        elif payload == 'mobile.last':
            main.reply_check_mobile_number(sender, data['entry'][0]['messaging'][0]['message']['text'], last_sender_message)
            payload = 'onai.amount'
        last_sender_message['payload'] = payload
        collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
        return "ok"
        collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
        return "ok"
         
    except:
        logging.info("No quick-reply payload")

    try:
        payload = data['entry'][0]['messaging'][0]['postback']['payload']
        if payload == 'GET_STARTED_PAYLOAD':
            #print (last_sender_message)
            fn, ln = get_firstname_lastname(sender)
            result = "Добро пожаловать в бот АО КазПочта, " + ln + " " + fn + "! "
            reply(sender, result)
            main.reply_main_menu_buttons(sender)
            return "ok"

        if payload == 'reroute':
            reply(sender, "[не работает] Введите трек-номер посылки\n" + hint_main_menu)
        elif payload == 'tracking':
            reply(sender, "Введите трек-номер посылки\n" + hint_main_menu)
        elif payload == 'extension':
            reply(sender, "[не работает] Введите трек-номер посылки\n" + hint_main_menu) 
        elif payload == 'shtrafy':
            main.reply_pdd_shtrafy(sender) 
        elif payload == 'komuslugi':
            main.reply_komuslugi_cities(sender) 
        elif payload == 'balance':
            try:
                encodedLoginPass = last_sender_message['encodedLoginPass']
                session = requests.Session()
                headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'], 'Content-Type':'application/json'}
                url_login = 'https://post.kz/mail-app/api/account/'
                r = session.get(url_login, headers=headers)
                assert r.status_code != 401
            except:
                reply(sender, "Требуется авторизация, пожалуйста, отправьте логин и пароль профиля на post.kz через пробел. Если у вас нет аккаунта то зарегистрируйтесь в https://post.kz/register")
                last_sender_message['payload'] = 'auth'
                collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
                return "need auth"

            hasCards = main.reply_has_cards(sender, last_sender_message)
            if not hasCards:
                reply(sender, "Добавьте карту в профиль post.kz в разделе \"Мои счета и карты\", пожалуйста")
                main.reply_main_menu_buttons(sender)
                last_sender_message['payload'] = 'mainMenu'
                collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
                return "need cards"

            last_sender_message['lastCommand'] = payload
            main.reply_mobile_enter_number(sender, last_sender_message)
        elif payload == 'card2card':
            reply(sender, "Выберите карту отправителя\n" + hint_main_menu)
            main.reply_card2card_chooseSrc(sender, last_sender_message) 
        elif payload == 'card2cash':
            reply(sender, "[не работает] Введите номер карты отправителя в формате\n0000 0000 0000 0000\n" + hint_main_menu)
        elif payload == 'courier':
            reply(sender, "[не работает] Отправьте геолокацию\n" + hint_main_menu)
        elif payload == 'currencies':
            main.reply_currencies(sender)
        elif payload == '10.kursy':
            main.reply_currencies_kursy(sender)
            main.reply_main_menu_buttons(sender)
        elif payload == '10.grafik':
            main.reply_currencies_grafik(sender)
        elif payload == 'closest':
            main.reply_closest(sender)
        elif payload == 'misc':
            main.reply_misc(sender)
        elif payload == 'onai':
            try:
                encodedLoginPass = last_sender_message['encodedLoginPass']
                assert encodedLoginPass != None
                session = requests.Session()
                headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'], 'Content-Type':'application/json'}
                url_login = 'https://post.kz/mail-app/api/account/'
                r = session.get(url_login, headers=headers)
                assert r.status_code != 401
            except:
                reply(sender, "Требуется авторизация, пожалуйста, отправьте логин и пароль профиля на post.kz через пробел. Если у вас нет аккаунта, то зарегистрируйтесь в https://post.kz/register")
                last_sender_message['payload'] = 'auth'
                collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
                return "need auth"

            hasCards = main.reply_has_cards(sender, last_sender_message)
            if not hasCards:
                reply(sender, "У вас нет подвязанной карты в профиле post.kz для оплаты пожалуйста добавьте карту https://post.kz/finance/cards/add\nТакже Вы можете переавторизоваться через Главное меню (нажмите (y) )-> Авторизация на post.kz")
                #main.reply_main_menu_buttons(sender)
                last_sender_message['payload'] = 'mainMenu'
                collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
                return "need cards"

            last_sender_message['lastCommand'] = payload
            main.reply_onai_enter_number(sender, last_sender_message)  
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
        elif payload == 'auth.delete':
            try:
                res = last_sender_message['encodedLoginPass']
                assert res != None
                last_sender_message['encodedLoginPass'] = None
                reply(sender, "Авторизация успешна удалена")
            except:
                reply(sender, "Авторизации нет")

        else:
            logging.info ("Ne raspoznana komanda")


        last_sender_message['payload'] = payload
        collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
        return "ok" 

    except:
        logging.info ("No postback payload")

    try:
        message = data['entry'][0]['messaging'][0]['message']['text']
        payload = last_sender_message['payload']
        if payload == 'tracking':
            main.reply_tracking(sender, message)
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
        elif payload == 'mobile.amount':
            main.reply_mobile_amount(sender, message, last_sender_message)
            return "ok"
        elif payload == 'mobile.chooseCard':
            main.reply_mobile_chooseCard(sender, message, last_sender_message)
            return "ok"
        elif payload == 'mobile.startPayment':
            main.reply_mobile_startPayment(sender, message, last_sender_message)
            return "ok"
        elif payload == 'mobile.finished' or payload =='onai.finished':
            return "ok"
        elif payload == 'onai':
            main.reply_onai(sender, message, last_sender_message)
            return "ok"
        elif payload == 'onai.amount':
            main.reply_onai_amount(sender, message, last_sender_message)
            return "ok"
        elif payload == 'onai.startPayment':
            main.reply_onai_startPayment(sender, message, last_sender_message)
            return "ok"
        main.reply_main_menu_buttons(sender)
        last_sender_message['payload'] = 'mainMenu'
        collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
        return "ok"

    except:
        logging.info ("No message")

    return "ok"
 
if __name__ == '__main__':
	app.run(debug=True, threaded=True)
