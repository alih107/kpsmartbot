import requests
import base64
import time
import pymongo
from datetime import datetime
import constants
import logging
import helper
import json

client = pymongo.MongoClient()
db = client.kpsmartbot_db
collection_messages = db.messages
url = constants.url
x_channel_id = constants.x_channel_id
portal_id = constants.portal_id
ACCESS_TOKEN = constants.ACCESS_TOKEN

hint_main_menu = "(для перехода в главное меню нажмите кнопку (y) "
hint_main_menu2 = "(Нажмите (y) для перехода в главное меню)"
card2card_info = "Информация:\nПереводы возможны только между картами одной МПС: Visa to Visa или MasterCard to MasterCard. \
\nПереводы между Visa и MasterCard возможны, только если одна из карт эмитирована банком АО \"Казкоммерцбанк\"."
timeout = 300

url_mobile_payments = 'https://post.kz/finance/payment/mobile'

def reply(sender, msg):
    data = {
        "recipient": {"id": sender},
        "message": {"text": msg}
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data)

def reply_typing_on(sender):
    data = {
        "recipient": {"id": sender},
        "sender_action": "typing_on"
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data)

def reply_typing_off(sender):
    data = {
        "recipient": {"id": sender},
        "sender_action": "typing_off"
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data)

def reply_display_cards(sender, last_sender_message):
    session = requests.Session()
    headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'], 'Content-Type': 'application/json'}
    url_login = 'https://post.kz/mail-app/api/account/'
    r = session.get(url_login, headers=headers)

    url_login6 = 'https://post.kz/mail-app/api/intervale/card?device=mobile'
    sd2 = {"blockedAmount": "", "phone": last_sender_message['mobileNumber'], "paymentId": "", "returnUrl": "",
           "transferId": ""}
    r = session.post(url_login6, json=sd2)
    cards = r.json()

    title = "Выберите карту"
    cards_group = []
    cards_array = []
    index = 0
    if len(cards) > 3:
        title = "Прокрутите влево/вправо, либо нажмите < или > для выбора других карт"
    for card in cards:
        if card['state'] == 'UNREGISTERED':
            continue
        if index % 3 == 0 and index > 0:
            cards_group.append({"title": title, "buttons": cards_array})
            cards_array = []
        card_title = card['title']
        if len(card_title) > 20:
            card_title = card['brand'] + ' *' + card['alias']
        cards_array.append({"type": "postback", "title": card_title, "payload": str(index)})
        last_sender_message[str(index)] = card_title
        index += 1

    cards_group.append({"title": title, "buttons": cards_array})

    data_cards = {
        "recipient": {
            "id": sender
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": cards_group
                }
            }
        }
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data_cards)
    collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)

def reply_send_redirect_url(sender, url):
    data_url_button = {
        "recipient": {
            "id": sender
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": "Для завершения платежа, введите код 3DSecure/MasterCode, нажав кнопку ниже",
                            "buttons": [
                                {
                                    "type": "web_url",
                                    "title": "3DSecure/MasterCode",
                                    "webview_height_ratio": "tall",
                                    "url": url
                                }
                            ]
                        }

                    ]
                }
            }
        }
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN,
                         json=data_url_button)
    reply_typing_off(sender)

def reply_pdd_shtrafy(sender):
    data_quick_replies = {
      "recipient":{
        "id": sender
      },
      "message":{
        "text":" Выберите:\n" + hint_main_menu2,
        "quick_replies":[
          {
            "content_type":"text",
            "title":"По ИИН",
            "payload":"4.IIN"
          },
          {
            "content_type":"text",
            "title":"Госномер, техпаспорт",
            "payload":"4.GosNomer"
          }
        ]
      }
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data_quick_replies)

def reply_pdd_shtrafy_iin(sender, message, last_sender_message):
    try:
        year = int(message[:2])
        month = int(message[2:4])
        day = int(message[4:6])
        century = int(message[6:7])
        assert month <= 12
        month31days = [1, 3, 5, 7, 8, 10, 12]
        month30days = [4, 6, 9, 11]
        if year % 4 == 0 and month == 2:
            assert day <= 28
        if month in month30days:
            assert day <= 30
        if month in month31days:
            assert day <= 31
        assert century <= 6
    except:
        reply(sender, "Вы ввели неправильный ИИН, введите еще раз")
        return "again"
    reply_typing_on(sender)
    session = requests.Session()
    url_login = 'https://post.kz/mail-app/api/public/transfer/loadName/' + message
    r = session.get(url_login).json()
    try:
        name = r['name']
    except:
        reply(sender, "Такой ИИН не найден, введите еще раз")
        return "again"

    try:
        headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'], 'Content-Type':'application/json'}
        url_login = 'https://post.kz/mail-app/api/account/'
        r = session.get(url_login, headers=headers)

        url_login = 'https://post.kz/mail-app/api/v2/subscriptions'
        data = {'operatorId':'pddIin', 'data':message}
        r = session.post(url_login, json=data)
        data = r.json()
        status = data['responseInfo']['status']
        if status == 'FAILED':
            result = 'Штрафов по данным ' + message + ' не найдено'
            reply(sender, result)
            reply_typing_off(sender)
            return "again"

        subscriptionId = str(r.json()['subscriptionData']['id'])
        url_login = 'https://post.kz/mail-app/api/v2/subscriptions/' + subscriptionId + '/invoices'
        invoiceData = session.get(url_login).json()['invoiceData']
        result = ''
        for fine in invoiceData:
            desc = fine['details'][0]['description']
            amount = str(fine['details'][0]['amount'])
            result += desc + ' - сумма ' + amount + ' тг\n\n'

        reply(sender, result)
        reply_typing_off(sender)

    except:
        url_login = 'https://post.kz/mail-app/api/public/v2/invoices/create'
        data = {'operatorId':'pddIin', 'data':message}
        r = session.post(url_login, json=data)
        data = r.json()
        status = data['responseInfo']['status']
        if status == 'FAILED':
            result = 'Штрафов по данным ' + message + ' не найдено\n'
            result += '(Информация может быть неполной! Для полной информации авторизуйтесь в главном меню)'
            reply(sender, result)
            reply_typing_off(sender)
            return "again"
        invoiceData = data['invoiceData']
        result = ''
        desc = invoiceData['details'][0]['description']
        amount = str(invoiceData['details'][0]['amount'])
        result += desc + ' - сумма ' + amount + ' тг\n'
        result += '(Информация может быть неполной! Для полной информации авторизуйтесь в главном меню)'

        reply_typing_off(sender)
        reply(sender, result)

def reply_pdd_shtrafy_gosnomer(sender, message, last_sender_message):
    reply(sender, "Идет проверка на наличие штрафов...")
    try:
        session = requests.Session()
        headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'], 'Content-Type':'application/json'}
        url_login = 'https://post.kz/mail-app/api/account/'
        r = session.get(url_login, headers=headers)

        url_login = 'https://post.kz/mail-app/api/v2/subscriptions'
        data = {'operatorId':'pddIin', 'data':message.replace(' ', '/')}
        r = session.post(url_login, json=data)
        data = r.json()
        status = data['responseInfo']['status']
        if status == 'FAILED':
            result = 'Штрафов по данным ' + message + ' не найдено'
            reply(sender, result)
            return "again"

        subscriptionId = str(r.json()['subscriptionData']['id'])
        url_login = 'https://post.kz/mail-app/api/v2/subscriptions/' + subscriptionId + '/invoices'
        invoiceData = session.get(url_login).json()['invoiceData']
        result = ''
        for fine in invoiceData:
            desc = fine['details'][0]['description']
            amount = str(fine['details'][0]['amount'])
            result += desc + ' - сумма ' + amount + ' тг\n\n'

        reply(sender, result)
    except:
        url_login = 'https://post.kz/mail-app/api/public/v2/invoices/create'
        data = {'operatorId':'pddIin', 'data':message}
        r = session.post(url_login, json=data)

def reply_onai(sender, message, last_sender_message):
    url_login = 'https://post.kz/mail-app/api/public/v2/invoices/create'
    message = message.replace(' ','')
    r = requests.post(url_login, json={"operatorId":"onai", "data":message})
    if r.status_code == 404:
        reply(sender, "Вы ввели неправильный номер карты Онай, введите еще раз")
        return "wrong onai number"

    last_sender_message['onaiToRefill'] = message
    last_sender_message['payload'] = 'onai.amount'
    collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
    reply(sender, "Введите сумму пополнения баланса (не менее 100 тг)")

def reply_onai_enter_number(sender, last_sender_message):
    try:
        lastOnaiNumber = helper.insert_space_onai(last_sender_message['onaiToRefill'])
        data_quick_replies = {
          "recipient":{
            "id": sender
          },
          "message":{
            "text":"Выберите карту Онай или введите 19ти-значный номер карты Онай\n" + hint_main_menu,
            "quick_replies":[
              {
                "content_type":"text",
                "title":lastOnaiNumber,
                "payload":"onai.last"
              }
            ]
          }
        }
        resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data_quick_replies)
    except:
        reply(sender, "Введите 19ти-значный номер карты Онай\n" + hint_main_menu)

def reply_onai_amount(sender, message, last_sender_message):
    amount = 0
    minAmount = 100
    try:
        amount = int(message)
    except:
        reply(sender, "Вы неправильно ввели сумму пополнения баланса. Введите сумму заново")
        return "again"

    if amount < minAmount:
        reply(sender, "Сумма пополнения баланса должна быть не менее " + str(minAmount) +" тг. Введите сумму заново")
        return "again"

    last_sender_message['payload'] = 'onai.chooseCard'
    last_sender_message['amount'] = amount
    collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
    reply_display_cards(sender, last_sender_message)

def reply_onai_csc(sender, payload, last_sender_message):
    amount = last_sender_message['amount']
    onaiToRefill = last_sender_message['onaiToRefill']
    chosenCard = last_sender_message[payload]
    
    message = "Вы ввели:\n"
    message += "Номер карты Онай: " + onaiToRefill + '\n'
    message += "Сумма: " + str(amount) + " тг\n"
    message += "Карта: " + chosenCard + '\n\n'
    message += "Если всё верно, введите трехзначный код CSC/CVV2 на обратной стороне карты"
    
    reply(sender, message)

def reply_onai_startPayment(sender, message, last_sender_message):
    reply(sender, "Идет обработка платежа...")
    reply_typing_on(sender)
    # 1 - авторизация на post.kz
    try:
        url_login = 'https://post.kz/mail-app/api/account/'
        headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'], 'Content-Type':'application/json'}

        session = requests.Session()
        r = session.get(url_login, headers=headers)
        iin = r.json()['iin']

        # 2 - вызов createSubscription() из PaymentAPI
        url_login2 = 'https://post.kz/mail-app/api/v2/subscriptions'
        login = last_sender_message['login']
        operatorId = 'onai'
        onaiToRefill = last_sender_message['onaiToRefill']
        amount = last_sender_message['amount']
        sd2 = {"id":"","login":login,"operatorId":operatorId,"data":onaiToRefill,"name":"","invoiceIds":""}
        r = session.post(url_login2, json=sd2)
        data = r.json()

        subscriptionId = str(data['subscriptionData']['id'])
        invoiceId = data['subscriptionData']['invoiceIds'][0]

        # 3 - вызов getInvoices() из PaymentAPI
        url_login3 = 'https://post.kz/mail-app/api/v2/subscriptions/' + subscriptionId + '/invoices'
        r = session.get(url_login3)
        body = r.json()['invoiceData'][0]

        # 4 - вызов getToken()
        url_login4 = 'https://post.kz/mail-app/api/intervale/token'
        mobileNumber = last_sender_message['mobileNumber']
        sd2 = {"blockedAmount":"","phone":mobileNumber,"paymentId":"","returnUrl":"","transferId":""}
        r = session.post(url_login4, json=sd2)
        token = r.json()['token']

        body['token'] = token
        body['invoiceId'] = invoiceId
        body['iin'] = iin
        body['systemId'] = 'POSTKZ'
        body['details'][0]['amount'] = amount
        body['details'][0]['commission'] = 0

        # 5 - вызов createPayment()
        url_login5 = 'https://post.kz/mail-app/api/v2/payments/create'
        r = session.post(url_login5, json=body)
        payment_id = r.json()['paymentData']['id']

        # 6 - вызов getCards()
        url_login6 = 'https://post.kz/mail-app/api/intervale/card?device=mobile'
        sd2 = {"blockedAmount":"","phone":mobileNumber,"paymentId":"","returnUrl":"","transferId":""}
        r = session.post(url_login6, json=sd2)

        card = r.json()[last_sender_message['chosenCardIndex']]
        sd2 = {}
        sd2['phone'] = mobileNumber
        sd2['paymentId'] = payment_id
        sd2['cardId'] = card['id']
        sd2['csc'] = message
        sd2['token'] = token
        sd2['returnUrl'] = 'https://post.kz/static/return.html'
        
        # 7 - вызов startPayment()
        url_login7 = 'https://post.kz/mail-app/api/intervale/payment/start/' + token
        r = session.post(url_login7, json=sd2)

        # 8 - вызов statusPayment()
        url_login8 = 'https://post.kz/mail-app/api/intervale/payment/status/' + token
        sd22 = {}
        sd22['phone'] = mobileNumber
        sd22['paymentId'] = payment_id
        r = session.post(url_login8, json=sd22)

        # 9 - вызов acceptPayment()
        url_login9 = 'https://post.kz/mail-app/api/intervale/payment/accept/' + token
        r = session.post(url_login9, json=sd2)

        # 10 - вызов statusPayment()
        url_login10 = 'https://post.kz/mail-app/api/intervale/payment/status/' + token
        r = session.post(url_login10, json=sd22)
        data = r.json()
        state = data['state']
        if state == 'redirect':
            reply_send_redirect_url(sender, data['url'])
            time.sleep(9)

        timer = 0
        while timer < timeout:
            time.sleep(1)
            r = session.post(url_login10, json=sd22)
            data = r.json()
            try:
                result_status = data['result']['status']
                if result_status == 'fail':
                    reply(sender, "Платеж не был завершен успешно. Попробуйте снова")
                elif result_status == 'success':
                    res = "Поздравляю! Платеж был проведен успешно, карта Онай " + onaiToRefill + " пополнена на сумму " + str(amount) + " тг.\n"
                    res += "Номер квитанции: " + str(payment_id)
                    res += ", она доступна в профиле post.kz в разделе История платежей"
                    reply(sender, res)
                last_sender_message['payload'] = 'onai.finished'
                collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
                reply_typing_off(sender)
                reply_main_menu_buttons(sender)
                return "ok"
            except Exception as e:
                pass
            timer += 1

        strminutes = str(timeout / 60)
        reply(sender, "Прошло больше " + strminutes + " минут: платеж отменяется")
        reply_typing_off(sender)
        reply_main_menu_buttons(sender)
        last_sender_message['payload'] = 'mainMenu'
        collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
        return "time exceed"
    except Exception as e:
        reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        reply_typing_off(sender)
        reply_main_menu_buttons(sender)
        return "fail"

def reply_card2card_enter_cardDst(sender, last_sender_message):
    try:
        lastCardDst = helper.insert_4_spaces(last_sender_message['lastCardDst'])
        data_quick_replies = {
          "recipient":{
            "id": sender
          },
          "message":{
            "text":card2card_info + "\n\nВыберите карту или введите 16ти-значный номер карты, на который Вы хотите перевести деньги\n" + hint_main_menu,
            "quick_replies":[
              {
                "content_type":"text",
                "title":lastCardDst,
                "payload":"card2card.last"
              }
            ]
          }
        }
        resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data_quick_replies)
    except:
        reply(sender, card2card_info + "\n\nВведите 16ти-значный номер карты, на который Вы хотите перевести деньги\n" + hint_main_menu)

def reply_card2card_check_cardDst(sender, message, last_sender_message):
    message = message.replace(' ', '')
    if len(message) != 16:
        reply(sender, "Вы ввели не все 16 цифр карты, попробуйте ещё раз")
        return "cardDst.again"
    if not helper.isAllDigits(message):
        reply(sender, "Некоторые введенные Вами цифры не являются цифрами, попробуйте ещё раз")
        return "cardDst.again"
    last_sender_message['lastCardDst'] = message
    last_sender_message['payload'] = 'card2card.amount'
    collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)
    reply(sender, "Введите сумму перевода (от 500 до 494070)\n" + hint_main_menu)

def reply_card2card_amount(sender, message, last_sender_message):
    amount = 0
    minAmount = 500
    maxAmount = 494070
    try:
        amount = int(message)
    except:
        reply(sender, "Вы неправильно ввели сумму перевода. Введите сумму заново")
        return "again"

    if amount < minAmount:
        reply(sender, "Сумма перевода должна быть не менее " + str(minAmount) + " тг. Введите сумму заново")
        return "again"

    if amount > maxAmount:
        reply(sender, "Сумма перевода должна быть не более " + str(maxAmount) + " тг. Введите сумму заново")
        return "again"

    last_sender_message['payload'] = 'card2card.chooseCard'
    last_sender_message['amount'] = amount
    collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)
    reply_display_cards(sender, last_sender_message)

def reply_card2card_csc(sender, payload, last_sender_message):
    amount = last_sender_message['amount']
    commission = amount * 1.2 / 100;
    if commission < 300:
        commission = 300
    lastCardDst = helper.insert_4_spaces(last_sender_message['lastCardDst'])
    total = amount + commission
    last_sender_message['commission'] = commission
    last_sender_message['total'] = commission
    chosenCard = last_sender_message[payload]

    message = "Вы ввели:\n"
    message += "Номер карты пополнения: " + lastCardDst + '\n'
    message += "Сумма: " + str(amount) + " тг\n"
    message += "Комиссия: " + str(commission) + " тг\n"
    message += "Итого: " + str(total) + " тг\n"
    message += "Карта: " + chosenCard + '\n\n'
    message += "Если всё верно, введите трехзначный код CSC/CVV2 на обратной стороне карты"

    reply(sender, message)

def reply_card2card_startPayment(sender, message, last_sender_message):
    reply(sender, "Идет обработка платежа...")
    reply_typing_on(sender)
    # 1 - авторизация на post.kz
    try:
        url_login = 'https://post.kz/mail-app/api/account/'
        headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'],
                   'Content-Type': 'application/json'}

        session = requests.Session()
        r = session.get(url_login, headers=headers)
        mobileNumber = last_sender_message['mobileNumber']

        # 2 - вызов getCards()
        url_login6 = 'https://post.kz/mail-app/api/intervale/card?device=mobile'
        sd2 = {"blockedAmount": "", "phone": mobileNumber, "paymentId": "", "returnUrl": "", "transferId": ""}
        r = session.post(url_login6, json=sd2)
        card = r.json()[last_sender_message['chosenCardIndex']]

        # 3 - вызов getToken()
        url_login4 = url + portal_id + '/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'X-Channel-Id': x_channel_id,
                   'X-IV-Authorization': 'Identifier ' + mobileNumber}
        r = session.post(url_login4, headers=headers)
        token = r.json()['token']

        # 4 - вызов startPayment()
        amount = last_sender_message['amount']
        data = {'paymentId': 'MoneyTransfer_KazPost_Card2Card',
                'currency': 'KZT',
                'amount': str(amount) + '00',
                'commission': str(last_sender_message['commission']) + '00',
                'total': str(last_sender_message['total']) + '00',
                'src.type': 'card_id',
                'src.cardId': card['id'],
                'src.csc': message,
                'dst.type': 'card',
                'dst.pan': last_sender_message['lastCardDst'],
                'returnUrl': 'https://transfer.post.kz/?token=' + token}

        url_login5 = url + portal_id + '/payment/' + token + '/start'
        r = session.post(url_login5, data=data, headers=headers)

        # 5 - вызов statusPayment()

        url_login10 = url + portal_id + '/payment/' + token
        r = session.post(url_login10, headers=headers)
        data = r.json()
        state = data['state']
        if state == 'redirect':
            reply_send_redirect_url(sender, data['url'])

        card_w_spaces = helper.insert_4_spaces(last_sender_message['lastCardDst'])
        timer = 0
        while timer < timeout:
            time.sleep(1)
            r = session.post(url_login10, headers=headers)
            data = r.json()
            try:
                result_status = data['result']['status']
                if result_status == 'fail':
                    reply(sender, "Платеж не был завершен успешно. Попробуйте снова")
                elif result_status == 'success':
                    res = "Поздравляю! Платеж был проведен успешно, карта " + card_w_spaces + " пополнена на сумму " + str(
                        amount) + " тг.\n"
                    res += "Номер квитанции: " + str(data['result']['trxId'])
                    res += ", она доступна в профиле post.kz в разделе История платежей"
                    reply(sender, res)
                last_sender_message['payload'] = 'card2card.finished'
                collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)
                reply_typing_off(sender)
                reply_main_menu_buttons(sender)
                return "ok"
            except Exception as e:
                pass
            timer += 1

        strminutes = str(timeout / 60)
        reply(sender, "Прошло больше " + strminutes + " минут: платеж отменяется")
        reply_typing_off(sender)
        reply_main_menu_buttons(sender)
        last_sender_message['payload'] = 'mainMenu'
        collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)
        return "time exceed"
    except Exception as e:
        reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        reply_typing_off(sender)
        reply_main_menu_buttons(sender)
        logging.error(helper.PrintException())
        return "fail"

def reply_balance(sender):
    data_balance_replies = {
      "recipient":{
        "id": sender
      },
      "message":{
        "text":"Выберите оператора\n" + hint_main_menu,
        "quick_replies":[
          {
            "content_type":"text",
            "title":"Tele2",
            "payload":"tele2Wf"
          },
          {
            "content_type":"text",
            "title":"Beeline",
            "payload":"beelineWf"
          },
          {
            "content_type":"text",
            "title":"Activ",
            "payload":"activWf"
          },
          {
            "content_type":"text",
            "title":"KCell",
            "payload":"kcellWf"
          }

        ]
      }
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data_balance_replies)

def reply_komuslugi_cities(sender):
    data_buttons_cities = {
      "recipient": {
        "id": sender
      },
      "message": {
        "attachment": {
          "type": "template",
          "payload": {
            "template_type": "generic",
            "elements": [
              {
                "title": "🏙️ Выберите город",
                "buttons": [
                  {
                    "type": "web_url",
                    "title": "Астана ЕРЦ",
                    "url":"https://post.kz/finance/paymentcomm/0",
                    "webview_height_ratio":"full"
                  },
                  #нужны кнопки 2 Актау
                  {
                    "type": "web_url",
                    "title": "Актау РЦКУ",
                    "url":"https://post.kz/finance/paymentcomm/7",
                    "webview_height_ratio":"full"
                  },
                  
                  {
                    "type": "web_url",
                    "title": "Актау МАЭК",
                    "url":"https://post.kz/finance/payment/maek",
                    "webview_height_ratio":"full"
                  }
                ]
              },
              {
                "title": "Выберите город",
                "buttons": [
                  {
                    "type": "web_url",
                    "title": "Атырау РЦКУ",
                    "url":"https://post.kz/finance/paymentcomm/8",
                    "webview_height_ratio":"full"
                  },
                  {
                    "type": "web_url",
                    "title": "Уральск РЦКУ",
                    "url":"https://post.kz/finance/paymentcomm/5",
                    "webview_height_ratio":"full"
                  },
                  {
                    "type": "web_url",
                    "title": "Запад РЦКУ (Уральск)",
                    "url":"https://post.kz/finance/paymentcomm/6",
                    "webview_height_ratio":"full"
                  }
                ]
              },
              {
                "title": "Выберите город",
                "buttons": [
                
                  {
                    "type": "web_url",
                    "title": "Костанай РЦКУ",
                    "url":"https://post.kz/finance/paymentcomm/9",
                    "webview_height_ratio":"full"
                  },
                  {
                    "type": "web_url",
                    "title": "Караганда ЕРЦ",
                    "url":"https://post.kz/finance/paymentcomm/2",
                    "webview_height_ratio":"full"
                  },
                  {
                    "type": "web_url",
                    "title": "Тараз РЦКУ",
                    "url":"https://post.kz/finance/paymentcomm/4",
                    "webview_height_ratio":"full"
                  }
                ]
              }
            ]
          }
        }
      }
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data_buttons_cities)

def reply_currencies(sender):
    data_cur_buttons = {
        "recipient": {"id": sender},
        "message":{
            "attachment":{
              "type":"template",
              "payload":{
                "template_type":"button",
                "text":"Выберите команду\n" + hint_main_menu,
                "buttons":[
                  {
                    "type":"postback",
                    "title":"💲 Курсы валют",
                    "payload":"10.kursy"
                  },
                  {
                    "type":"postback",
                    "title":"💹 График изменения",
                    "payload":"10.grafik"
                  },
                  {
                    "type":"postback",
                    "title":"🔔 Настр. уведомлений",
                    "payload":"10.nastroika"
                  }
                ]
              }
            }
          }
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data_cur_buttons)

def reply_currencies_grafik(sender):
    data_cur_grafik_buttons = {
        "recipient": {"id": sender},
        "message":{
            "attachment":{
              "type":"template",
              "payload":{
                "template_type":"button",
                "text":"[не работает] Выберите валюту\n" + hint_main_menu,
                "buttons":[
                  {
                    "type":"postback",
                    "title":"🇺🇸 USD",
                    "payload":"10.grafik_USD"
                  },
                  {
                    "type":"postback",
                    "title":"🇪🇺 EUR",
                    "payload":"10.grafik_EUR"
                  },
                  {
                    "type":"postback",
                    "title":"🇷🇺 RUB",
                    "payload":"10.grafik_RUB"
                  }
                ]
              }
            }
          }
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data_cur_grafik_buttons)

def reply_tracking(sender, tracking_number, last_sender_message):
    data = requests.get("https://post.kz/external-api/tracking/api/v2/" + tracking_number + "/events").json()
    data2 = requests.get("https://post.kz/external-api/tracking/api/v2/" + tracking_number).json()
    try:
        error = data2['error']
        reply(sender, error + '\n(Чтобы узнать статус другой посылки, отправьте её трек-номер либо нажмите (y) для перехода в главное меню)')
        return "not found"
    except:
        last_sender_message['lastTrackingNumber'] = tracking_number
        collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)
        new_mapping = requests.get("https://post.kz/static/new_mappings.json").json()
        t_date = data['events'][0]['date']
        t_time = data['events'][0]['activity'][0]['time']
        t_datetime = t_date + " " + t_time
        t_status = data['events'][0]['activity'][0]['status'][0]
        t_address = data2['last']['address']
        t_status_mapping = new_mapping[t_status]['mapping']
        result = "Информация об отправлении " + tracking_number + '\n'
        result += "Статус: " + t_status_mapping + '\n' + t_address + '\n' + t_datetime + '\n'
        result += "(Чтобы узнать статус другой посылки, отправьте её трек-номер либо нажмите (y) для перехода в главное меню)" + '\n'
        
        reply(sender, result)
        return "ok"

def reply_currencies_kursy(sender):
    data = requests.get("https://post.kz/mail-app/info/remote/currencies/ops").json()
    result = "Курс валют на " + datetime.now().strftime('%d.%m.%Y %H:%M:%S') + " (время западное GMT +5)\n" 
    result += "USD: " + data['usdBuy'] + " / " + data['usdSell'] + '\n'
    result += "EUR: " + data['eurBuy'] + " / " + data['eurSell'] + '\n'
    result += "RUB: " + data['rurBuy'] + " / " + data['rurSell']
    reply(sender, result)

def reply_auth(sender, loginPass, last_sender_message):
    url_login = 'https://post.kz/mail-app/api/account/'
    login = loginPass.split()[0]
    loginPass = loginPass.replace(' ', ':').encode()
    encodedLoginPass = base64.b64encode(loginPass).decode("utf-8")
    headers = {"Authorization": "Basic " + encodedLoginPass}

    r = requests.get(url_login, headers=headers)
    status_code = r.status_code
    if status_code == 401:
        reply(sender, "Вы ввели неправильные логин и пароль, попробуйте еще раз")
    elif status_code == 200:
        profile_data = r.json()
        iin = profile_data['iin']
        mobile = profile_data['mobileNumber']
        answer = "Вы успешно авторизованы! Добро пожаловать, " + profile_data['firstName'] + "!\n"
        answer += "В целях безопасности удалите сообщение с вашими логином и паролем"
        reply(sender, answer)
        last_sender_message['encodedLoginPass'] = encodedLoginPass
        last_sender_message['login'] = login
        last_sender_message['iin'] = iin
        last_sender_message['mobileNumber'] = mobile
        collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
        reply_main_menu_buttons(sender)

def reply_closest(sender):
    data_closest_buttons = {
        "recipient": {"id": sender},
        "message":{
            "attachment":{
              "type":"template",
              "payload":{
                "template_type":"button",
                "text":"[не работает] Найти ближайшие\n" + hint_main_menu,
                "buttons":[
                  {
                    "type":"postback",
                    "title":"📦 Постаматы",
                    "payload":"11.postamats"
                  },
                  {
                    "type":"postback",
                    "title":"🏢 Отделения",
                    "payload":"11.postal_offices"
                  },
                  {
                    "type":"postback",
                    "title":"🏧 Банкоматы",
                    "payload":"11.atms"
                  }
                ]
              }
            }
          }
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data_closest_buttons)

def reply_misc(sender):
    data_misc_buttons = {
        "recipient": {"id": sender},
        "message":{
            "attachment":{
              "type":"template",
              "payload":{
                "template_type":"button",
                "text":" Выберите команду\n" + hint_main_menu,
                "buttons":[
                  {
                    "type":"web_url",
                    "title":"📝 Работа в КазПочте",
                    "url":"https://post.kz/info/7/o-kompanii/item/273/vacancy",
                    "webview_height_ratio":"full"
                  },
                  {
                    "type":"web_url",
                    "title":"📜Проверить квитанцию",
                    "url":"https://post.kz/invoice",
                    "webview_height_ratio":"full"
                  },
                  {
                    "type":"web_url",
                    "title":"🏢 Посетить отделение",
                    "url":"https://post.kz/departments/list",
                    "webview_height_ratio":"full"
                  }
                ]
              }
            }
          }
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data_misc_buttons)

def reply_main_menu_buttons(sender):
    url = "https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN
    title = "Прокрутите влево/вправо, либо нажмите < или > для других команд"
    data_main_menu_buttons = {
      "recipient": {
        "id": sender
      },
      "message": {
        "attachment": {
          "type": "template",
          "payload": {
            "template_type": "generic",
            "elements": [
              {
                "title": title,
                "buttons": [
                  {
                    "type": "postback",
                    "title": "💳 Перевод на карту",
                    "payload": "card2card"
                  },
                  {
                    "type": "postback",
                    "title": "🚌 Онай",
                    "payload": "onai"
                  },
                  {
                    "type": "postback",
                    "title": "📲 Пополнение баланса",
                    "payload": "balance"
                  }
                ]
              },
              {
                "title": title,
                "buttons": [
                  {
                    "type": "postback",
                    "title": "💲 Курсы валют",
                    "payload": "10.kursy"
                  },
                  {
                    "type": "postback",
                    "title": "🔍 Отслеживание",
                    "payload": "tracking"
                  },
                  {
                    "type": "postback",
                    "title": "📍 Ближайшие",
                    "payload": "nearest"
                  }
                ]
              },              
              {
                "title": "Платежи",
                "buttons": [
                  {
                    "type": "postback",
                    "title": "🚗 Штрафы ПДД",
                    "payload": "shtrafy"
                  },
                  {
                    "type": "web_url",
                    "title": "💸 Перевод на руки",
                    "url":"https://transfer.post.kz/money-transfer/card-to-cash",
                    "webview_height_ratio":"full"
                  },
                  {
                    "type": "postback",
                    "title": "📃 Оплата ком.услуг",
                    "payload": "komuslugi"
                  }
                 
                ]
              },
              {
                "title": "Прочие услуги",
                "buttons": [  
                  {
                    "type": "web_url",
                    "title": "⚖️ Cудебные штрафы",
                    "url":"https://post.kz/finance/payment/fines",
                    "webview_height_ratio":"full"
                  },
                  {
                    "type": "postback",
                    "title": "📁 Прочее",
                    "payload": "misc"
                  }
                ]
              },
              {
                "title": "Профиль на post.kz",
                "buttons": [  
                  {
                    "type": "postback",
                    "title": "Удаление авторизации",
                    "payload": "auth.delete"
                  },
                  {
                    "type": "postback",
                    "title": "Авторизация",
                    "payload": "auth"
                  },
                  {
                    "type": "postback",
                    "title": "Добавить карту",
                    "payload": "addcard"
                  }
                ]
              }
            ]
          }
        }
      }
    }
    resp = requests.post(url, json=data_main_menu_buttons)

def reply_mobile_enter_number(sender, last_sender_message):
    try:
        lastPhoneToRefill = last_sender_message['phoneToRefill']
        data_quick_replies = {
          "recipient":{
            "id": sender
          },
          "message":{
            "text":"Выберите номер телефона или введите его\n" + hint_main_menu,
            "quick_replies":[
              {
                "content_type":"text",
                "title":lastPhoneToRefill,
                "payload":"mobile.last"
              }
            ]
          }
        }
        resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data_quick_replies)
    except:
        reply(sender, "Введите номер телефона\n" + hint_main_menu)

def reply_check_mobile_number(sender, message, last_sender_message):
    url_login = 'https://post.kz/mail-app/public/check/operator'
    message = message.replace(' ', '')
    message = message[-10:]
    r = requests.post(url_login, json={"phone":message})
    operator = r.json()['operator']
    
    if operator == 'error':
        reply(sender, "Вы ввели неправильный номер телефона. Попробуйте еще раз")
        return "error"

    operator = operator[:-2].title()
    minAmount = 0
    if operator == 'Tele2' or operator == 'Beeline':
        minAmount = 100
    elif operator == 'Activ' or operator == 'Kcell':
        minAmount = 200
    else:
        reply(sender, "Оператор " + operator +" сейчас не поддерживается. Введите другой номер, пожалуйста.")

    last_sender_message['mobileOperator'] = operator
    last_sender_message['payload'] = 'mobile.amount'
    last_sender_message['phoneToRefill'] = message
    last_sender_message['minAmount'] = minAmount
    collection_messages.update_one({'sender': sender}, {"$set": last_sender_message}, upsert=False)
    reply(sender, "Оператор номера: " + operator + "\nВведите сумму пополнения баланса (не менее " + str(minAmount) + " тг)")
    
def reply_mobile_amount(sender, message, last_sender_message):
    amount = 0
    minAmount = last_sender_message['minAmount']
    try:
        amount = int(message)
    except:
        reply(sender, "Вы неправильно ввели сумму пополнения баланса. Введите сумму заново")
        return "again"

    if amount < minAmount:
        reply(sender, "Сумма пополнения баланса должна быть не менее " + str(minAmount) +" тг. Введите сумму заново")
        return "again"

    last_sender_message['payload'] = 'mobile.chooseCard'
    last_sender_message['amount'] = amount
    collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
    reply_display_cards(sender, message, last_sender_message)

def reply_mobile_csc(sender, payload, last_sender_message):
    amount = last_sender_message['amount']
    commission = 0
    operator = last_sender_message['mobileOperator']
    if operator == 'activWf' or operator == 'kcellWf':
        commission = amount / 10
        if commission > 70:
            commission = 70
    elif operator == 'tele2Wf' or operator == 'beelineWf':
        commission = 50
    phoneToRefill = last_sender_message['phoneToRefill']
    total = amount + commission
    chosenCard = last_sender_message[payload]
    
    message = "Вы ввели:\n"
    message += "Номер телефона: " + phoneToRefill + '\n'
    message += "Сумма: " + str(amount) + " тг\n"
    message += "Комиссия: " + str(commission) + " тг\n"
    message += "Итого: " + str(total) + " тг\n"
    message += "Карта: " + chosenCard + '\n\n'
    message += "Если всё верно, введите трехзначный код CSC/CVV2 на обратной стороне карты"
    
    reply(sender, message)

def reply_mobile_startPayment(sender, message, last_sender_message):
    reply(sender, "Идет обработка платежа...")
    reply_typing_on(sender)
    # 1 - авторизация на post.kz
    try:
        url_login = 'https://post.kz/mail-app/api/account/'
        headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'], 'Content-Type':'application/json'}

        session = requests.Session()
        r = session.get(url_login, headers=headers)
        iin = r.json()['iin']

        # 2 - вызов createSubscription() из PaymentAPI
        url_login2 = 'https://post.kz/mail-app/api/v2/subscriptions'
        login = last_sender_message['login']
        operatorId = last_sender_message['mobileOperator']
        phoneToRefill = last_sender_message['phoneToRefill']
        amount = last_sender_message['amount']
        sd2 = {"id":"","login":login,"operatorId":operatorId,"data":phoneToRefill,"name":"","invoiceIds":""}
        r = session.post(url_login2, json=sd2)
        data = r.json()

        subscriptionId = str(data['subscriptionData']['id'])
        invoiceId = data['subscriptionData']['invoiceIds'][0]

        # 3 - вызов getInvoices() из PaymentAPI
        url_login3 = 'https://post.kz/mail-app/api/v2/subscriptions/' + subscriptionId + '/invoices'
        r = session.get(url_login3)
        body = r.json()['invoiceData'][0]

        # 4 - вызов getToken()
        url_login4 = 'https://post.kz/mail-app/api/intervale/token?device=mobile'
        mobileNumber = last_sender_message['mobileNumber']
        sd2 = {"blockedAmount":"","phone":mobileNumber,"paymentId":"","returnUrl":"","transferId":""}
        r = session.post(url_login4, json=sd2)
        token = r.json()['token']

        body['token'] = token
        body['invoiceId'] = invoiceId
        body['iin'] = iin
        body['systemId'] = 'mobile'
        body['details'][0]['amount'] = amount
        body['details'][0]['commission'] = last_sender_message['commission']
        #print ('#############################################')
        #print (body)

        # 5 - вызов createPayment()
        url_login5 = 'https://post.kz/mail-app/api/v2/payments/create?device=mobile'
        r = session.post(url_login5, json=body)
        payment_id = r.json()['paymentData']['id']
        #print ('#############################################')
        #print (r.json())

        # 6 - вызов getCards()
        url_login6 = 'https://post.kz/mail-app/api/intervale/card?device=mobile'
        sd2 = {"blockedAmount":"","phone":mobileNumber,"paymentId":"","returnUrl":"","transferId":""}
        r = session.post(url_login6, json=sd2)

        card = r.json()[last_sender_message['chosenCardIndex']]
        sd2 = {}
        sd2['phone'] = mobileNumber
        sd2['paymentId'] = payment_id
        sd2['cardId'] = card['id']
        sd2['csc'] = message
        sd2['token'] = token
        sd2['returnUrl'] = 'https://post.kz/static/return.html'
        
        # 7 - вызов startPayment()
        url_login7 = 'https://post.kz/mail-app/api/intervale/payment/start/' + token + '?device=mobile'
        r = session.post(url_login7, json=sd2)

        # 8 - вызов statusPayment()
        url_login8 = 'https://post.kz/mail-app/api/intervale/payment/status/' + token + '?device=mobile'
        sd22 = {}
        sd22['phone'] = mobileNumber
        sd22['paymentId'] = payment_id
        r = session.post(url_login8, json=sd22)

        # 9 - вызов acceptPayment()
        url_login9 = 'https://post.kz/mail-app/api/intervale/payment/accept/' + token + '?device=mobile'
        r = session.post(url_login9, json=sd2)

        # 10 - вызов statusPayment()
        url_login10 = 'https://post.kz/mail-app/api/intervale/payment/status/' + token + '?device=mobile'
        r = session.post(url_login10, json=sd22)
        data = r.json()
        state = data['state']
        if state == 'redirect':
            reply_send_redirect_url(sender, data['url'])
            time.sleep(9)

        timer = 0
        while timer < timeout:
            time.sleep(1)
            r = session.post(url_login10, json=sd22)
            data = r.json()
            try:
                result_status = data['result']['status']
                if result_status == 'fail':
                    reply(sender, "Платеж не был завершен успешно. Попробуйте снова")
                elif result_status == 'success':
                    res = "Поздравляю! Платеж был проведен успешно, номер " + phoneToRefill + " пополнен на сумму " + str(amount) + " тг.\n"
                    res += "Номер квитанции: " + str(payment_id)
                    res += ", она доступна в профиле post.kz в разделе История платежей"
                    reply(sender, res)
                last_sender_message['payload'] = 'mobile.finished'
                collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
                reply_typing_off(sender)
                reply_main_menu_buttons(sender)
                return "ok"
            except Exception as e:
                pass
            timer += 1

        strminutes = str(timeout / 60)
        reply(sender, "Прошло больше " + strminutes + " минут: платеж отменяется")
        reply_typing_off(sender)
        reply_main_menu_buttons(sender)
        last_sender_message['payload'] = 'mainMenu'
        collection_messages.update_one({'sender':sender}, {"$set": last_sender_message}, upsert=False)
        return "time exceed"
    except Exception as e:
        reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        reply_typing_off(sender)
        reply_main_menu_buttons(sender)
        return "fail"

def reply_has_cards(sender, last_sender_message):
    session = requests.Session()
    headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'], 'Content-Type':'application/json'}
    url_login = 'https://post.kz/mail-app/api/account/'
    r = session.get(url_login, headers=headers)
    
    url_login6 = 'https://post.kz/mail-app/api/intervale/card?device=mobile'
    sd2 = {"blockedAmount":"","phone":last_sender_message['mobileNumber'],"paymentId":"","returnUrl":"","transferId":""}
    r = session.post(url_login6, json=sd2)
    cardsCount = len(r.json())
    return cardsCount > 0

def reply_nearest(sender):
    data_misc_buttons = {
        "recipient": {"id": sender},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": " Выберите команду\n" + hint_main_menu,
                    "buttons": [
                        {
                            "type": "postback",
                            "title": "📦 Постаматы",
                            "payload": "nearest.postamats"
                        },
                        {
                            "type": "postback",
                            "title": "🏢 Отделения",
                            "payload": "nearest.offices"
                        },
                        {
                            "type": "postback",
                            "title": "🏧 Банкоматы",
                            "payload": "nearest.atms"
                        }
                    ]
                }
            }
        }
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN,
                         json=data_misc_buttons)

def reply_nearest_request_location(sender):
    reply(sender, 'Отправьте своё местоположение (нажмите ➕)')

def reply_nearest_find(sender, locLong, locLat, payload):
    try:
        fileName = ''
        title = ''

        if payload != 'nearest.offices':
            if payload == 'nearest.postamats':
                fileName = 'postamats.json'
                title = 'Ближайший Постамат'
            elif payload == 'nearest.atms':
                fileName = 'atms.json'
                title = 'Ближайший Банкомат'

            with open('initial_data/' + fileName) as json_data:
                d = json.load(json_data)

            items = []
            for model in d:
                if model['fields']['is_active']:
                    dist = helper.get_distance_in_meters(locLat, float(model['fields']['latitude']), locLong, float(model['fields']['longitude']))
                    items.append((model['fields'], dist))

            items.sort(key=lambda x: x[1])
            closestLoc = items[0][0]

            res = title + ':\n'
            if payload == 'nearest.postamats':
                res += closestLoc['full_name'] + '\n'
                res += 'Город: ' + closestLoc['city'] + '\n'
                res += 'Индекс: ' + closestLoc['postcode'] + '\n'
                if closestLoc['postcode_new'] != None:
                    res += 'Новый индекс: ' + closestLoc['postcode_new'] + '\n'

            if payload == 'nearest.atms':
                res += closestLoc['address'] + '\n'
            res += 'Расстояние: ' + str(items[0][1]) + ' м.'
            reply(sender, res)
            reply_nearest_map_location(sender, closestLoc['longitude'], closestLoc['latitude'], title)
        else:
            title = 'Ближайшее Отделение'
            url = 'http://test.monitor.kazpost.kz/api/jsons/find_dep.json?'
            url += 'lat=' + str(locLat).replace('.', ',') + '&lng=' + str(locLong).replace('.', ',')
            r = requests.get(url)
            try:
                data = r.json()
            except:
                data = r.text
                a = data.find('\"answer\":\"') + 10
                b = data.find('\"}')
                answer = data[a:b].replace('\"', '\\\"')
                part1 = data.split('\"answer\":\"')[0]
                result = part1 + '\"answer\":\"' + answer + '\"}'
                data = json.loads(result)
            reply(sender, data['answer'])
            reply_nearest_map_location(sender, data['longitude'].replace(',', '.'), data['latitude'].replace(',', '.'), title)

    except:
        reply(sender, 'Сервис временно недоступен, попробуйте позднее')

def reply_nearest_map_location(sender, locLong, locLat, title):
    latCommaLong = str(locLat) + ',' + str(locLong)
    image_url = 'https://maps.googleapis.com/maps/api/staticmap?size=764x400&center='
    image_url += latCommaLong + '&zoom=15&markers=' + latCommaLong
    web_url = 'https://www.google.com/maps/place/' + latCommaLong
    data_misc_buttons = {
      "recipient":{ "id":sender },
      "message":{
        "attachment":{
          "type":"template",
          "payload":{
            "template_type":"generic",
            "elements":[
               {
                "title":title,
                "image_url":image_url,
                "default_action": {
                  "type": "web_url",
                  "url": web_url
                }
              }
            ]
          }
        }
      }
    }

    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN,
                         json=data_misc_buttons)