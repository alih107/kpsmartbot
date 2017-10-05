import main
import helper
import requests
import logging
import math
fb_url = main.fb_url
url = main.url
portal_id = main.portal_id
x_channel_id = main.x_channel_id


def get_komuslugi(last_sender_message, data):
    message = data['data']
    result = ''
    session = requests.Session()
    status = 'FAILED'
    try:
        headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'],
                   'Content-Type': 'application/json'}
        url_login = 'https://post.kz/mail-app/api/account/'
        r = session.get(url_login, headers=headers)

        url_login = 'https://post.kz/mail-app/api/v2/subscriptions'
        r = session.post(url_login, json=data)
        data = r.json()
        status = data['responseInfo']['status']
        if status == 'FAILED':
            result = 'Квитанций по лицевому счёту ' + message + ' не найдено\n'
        else:
            sum = 0
            subscriptionId = str(r.json()['subscriptionData']['id'])
            url_login = 'https://post.kz/mail-app/api/v2/subscriptions/' + subscriptionId + '/invoices'
            data = session.get(url_login).json()
            status = data['responseInfo']['status']
            invoiceData = data['invoiceData'][0]
            result = 'Информация по лицевому счёту ' + message + '\n'
            result += invoiceData['description'] + '\n\n'
            for i in invoiceData['details']:
                desc = i['description']
                amount = i['amount']
                amount_str = ', сумма ' + str(amount) + ' тг'
                debt = i['debt']
                sum += amount + debt
                debt_str = ''
                if debt > 0:
                    debt_str = ', долг ' + str(debt) + ' тг'
                result += desc + debt_str + amount_str + '\n'
            result += '\nИтого: ' + format(sum, '.2f') + ' тг'
    except:
        main.reply(last_sender_message['sender'], "Произошла непредвиденная ошибка, попробуйте позднее")
        logging.error(helper.PrintException())
        return 'error', status
    return result, status

def get_komuslugi_invoice(last_sender_message):
    message = last_sender_message['astanaErc_last_acc']
    data = {'operatorId': 'astanaErcWf', 'data': message}
    session = requests.Session()
    invoiceData = {}
    try:
        headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'],
                   'Content-Type': 'application/json'}
        url_login = 'https://post.kz/mail-app/api/account/'
        r = session.get(url_login, headers=headers)

        url_login = 'https://post.kz/mail-app/api/v2/subscriptions'
        r = session.post(url_login, json=data)
        subscriptionId = str(r.json()['subscriptionData']['id'])
        url_login = 'https://post.kz/mail-app/api/v2/subscriptions/' + subscriptionId + '/invoices'
        data = session.get(url_login).json()
        invoiceData = data['invoiceData'][0]
    except:
        main.reply(last_sender_message['sender'], "Произошла непредвиденная ошибка, попробуйте позднее")
        logging.error(helper.PrintException())
    return invoiceData

def reply_komuslugi_cities(sender):
    data_buttons_cities = {
        "recipient": {"id": sender},
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
                                    "type": "postback",
                                    "title": "Астана ЕРЦ",
                                    "payload": "astanaErc"
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }
    requests.post(fb_url, json=data_buttons_cities)

def reply_astanaErc_enter(sender, last_sender_message):
    astanaErc_accounts = []
    try:
        astanaErc_accounts = last_sender_message['astanaErc_accounts']
    except:
        last_sender_message['astanaErc_accounts'] = []

    try:
        assert len(astanaErc_accounts) > 0
        buttons = []
        for acc in astanaErc_accounts:
            buttons.append({"content_type": "text", "payload": "astanaErc.last", "title": acc})
        buttons.append({"content_type": "text", "payload": "astanaErc.delete", "title": "Удалить лицевой счёт"})
        data_quick_replies = {
            "recipient": {"id": sender},
            "message": {
                "text": "Выберите номер лицевого счёта Астана ЕРЦ или введите его\n" + main.hint_main_menu,
                "quick_replies": buttons
            }
        }
        requests.post(fb_url, json=data_quick_replies)
    except:
        main.reply(sender, "Введите номер лицевого счёта Астана ЕРЦ\n" + main.hint_main_menu)
    last_sender_message['payload'] = 'astanaErc.enter'
    main.mongo_update_record(last_sender_message)

def reply_astanaErc(sender, message, last_sender_message):
    main.reply_typing_on(sender)
    try:
        if not main.check_login(sender, last_sender_message):
            return
        data = {'operatorId': 'astanaErcWf', 'data': message}
        result, status = get_komuslugi(last_sender_message, data)
        if result == 'error':
            return
        if not "astanaErc_accounts" in last_sender_message:
            last_sender_message['astanaErc_accounts'] = []
        if not message in last_sender_message['astanaErc_accounts'] and len(last_sender_message['astanaErc_accounts']) < 10:
            last_sender_message['astanaErc_accounts'].append(message)

        reply_astanaErc_quick_replies_with_delete(sender, last_sender_message['astanaErc_accounts'], result, status)
        last_sender_message['astanaErc_last_acc'] = message
        main.mongo_update_record(last_sender_message)
    except:
        logging.error(helper.PrintException())

def reply_astanaErc_quick_replies_with_delete(sender, astanaErc_accounts, text, status):
    main.reply(sender, text)
    data_text = "(Вы можете оплатить квитанцию, выбрать или ввести номер лицевого счёта Астана ЕРЦ, чтобы посмотреть " \
                "квитанции, либо нажать (y) для перехода в главное меню)"
    buttons = []
    if status == 'OK':
        buttons.append({"content_type": "text", "payload": "astanaErc.pay", "title": "Оплатить квитанцию"})
    for acc in astanaErc_accounts:
        buttons.append({"content_type": "text", "payload": "astanaErc.last", "title": acc})
    buttons.append({"content_type": "text", "payload": "astanaErc.delete", "title": "Удалить лицевой счёт"})
    data_quick_replies = {
        "recipient": {"id": sender},
        "message": {
            "text": data_text,
            "quick_replies": buttons
        }
    }
    requests.post(fb_url, json=data_quick_replies)

def reply_astanaErc_delete(sender, last_sender_message):
    astanaErc_accounts = last_sender_message['astanaErc_accounts']
    buttons = []
    for acc in astanaErc_accounts:
        buttons.append({"content_type": "text", "payload": "astanaErc.delete.acc", "title": acc})

    data_quick_replies = {
        "recipient": {"id": sender},
        "message": {
            "text": "Выберите лицевой счёт, чтобы его удалить",
            "quick_replies": buttons
        }
    }
    requests.post(fb_url, json=data_quick_replies)

def reply_astanaErc_delete_acc(sender, text, last_sender_message):
    last_sender_message['astanaErc_accounts'].remove(text)
    main.reply(sender, "Лицевой счёт " + text + " успешно удалён")
    reply_astanaErc_enter(sender, last_sender_message)
    last_sender_message['payload'] = 'astanaErc.enter'
    main.mongo_update_record(last_sender_message)

def reply_astanaErc_chooseCard(sender, last_sender_message):
    main.reply_typing_on(sender)
    main.reply_display_cards(sender, last_sender_message)
    last_sender_message['lastCommand'] = 'astanaErc'
    main.mongo_update_record(last_sender_message)

def reply_astanaErc_csc(sender, payload, last_sender_message):
    main.reply_typing_on(sender)
    chosenCard = last_sender_message[payload]
    result = 'Проверьте суммы:\n'
    invoiceData = get_komuslugi_invoice(last_sender_message)
    c = 0
    sum = 0
    for i in invoiceData['details']:
        desc = i['description']
        invoiceData['details'][c]['amount'] = math.ceil(invoiceData['details'][c]['amount'])
        amount = i['amount']
        debt = i['debt']
        sum += amount + debt
        sum_str = ', сумма ' + str(amount + debt) + ' тг'
        result += desc + sum_str + '\n'
        c += 1
    result += '\nИтого: ' + str(sum) + ' тг'
    result += "\nКарта: " + chosenCard + '\n\n'
    result += "Если всё верно, введите трехзначный код CSC/CVV2 на обратной стороне карты"
    main.reply(sender, result)
    last_sender_message['payload'] = 'astanaErc.startPayment'
    main.mongo_update_record(last_sender_message)

def reply_astanaErc_startPayment(sender, message, last_sender_message):
    if not helper.check_csc(message):
        main.reply(sender, "Вы неправильно ввели трёхзначный код CSC/CVV2 на обратной стороне карты, введите заново")
        return "ok"
    main.reply(sender, "Идет обработка платежа...")
    main.reply_typing_on(sender)
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
                mongo_update_record(last_sender_message)
                reply_typing_off(sender)
                reply_main_menu_buttons(sender)
                return "ok"
            except Exception as e:
                pass
            timer += 1

        last_sender_message = collection_messages.find_one({"sender": sender})
        if last_sender_message['payload'] == 'card2card.startPayment':
            strminutes = str(timeout // 60)
            reply(sender, "Прошло больше " + strminutes + " минут: платеж отменяется")
            reply_typing_off(sender)
            reply_main_menu_buttons(sender)
            last_sender_message['payload'] = 'mainMenu'
            mongo_update_record(last_sender_message)
        return "time exceed"
    except Exception as e:
        reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        reply_typing_off(sender)
        reply_main_menu_buttons(sender)
        logging.error(helper.PrintException())
        return "fail"