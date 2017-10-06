import main
import helper
import requests
import logging
import math
import time
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
    invoiceData = {}
    try:
        session = main.get_authorized_session(last_sender_message['encodedLoginPass'])
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
    try:
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
        result += "\nКарта: " + chosenCard
        result += "\nСумма: " + str(sum) + " тг"
        result += "\nКомиссия: 100 тг"
        #result += "\nИтого: " + str(sum + 100.0) + " тг"
        result += "\n\nЕсли всё верно, введите трехзначный код CSC/CVV2 на обратной стороне карты"
        main.reply(sender, result)
    except:
        logging.error(helper.PrintException())

def reply_astanaErc_startPayment(sender, message, last_sender_message):
    if not helper.check_csc(message):
        main.reply(sender, "Вы неправильно ввели трёхзначный код CSC/CVV2 на обратной стороне карты, введите заново")
        return "ok"
    main.reply(sender, "Идет обработка платежа...")
    main.reply_typing_on(sender)
    # 1 - авторизация на post.kz
    try:
        session = main.get_authorized_session(last_sender_message['encodedLoginPass'])
        mobileNumber = last_sender_message['mobileNumber']
        token = main.get_token_postkz(session, mobileNumber)
        invoiceData = get_komuslugi_invoice(last_sender_message)
        invoiceData['systemId'] = 'POSTKZ'
        invoiceData['token'] = token
        invoiceData['invoiceId'] = invoiceData['id']
        c = 0
        for i in invoiceData['details']:
            invoiceData['details'][c]['amount'] = math.ceil(invoiceData['details'][c]['amount'])
            c += 1

        # 5 - createPayment
        url_login5 = 'https://post.kz/mail-app/api/v2/payments/create'
        r = session.post(url_login5, json=invoiceData)
        payment_id = r.json()['paymentData']['id']

        # 6 - вызов getCards()
        url_login6 = 'https://post.kz/mail-app/api/intervale/card?device=mobile'
        sd2 = {"blockedAmount": "", "phone": mobileNumber, "paymentId": "", "returnUrl": "", "transferId": ""}
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
        if data['state'] == 'redirect':
            main.reply_send_redirect_url(sender, data['url'])
            time.sleep(5)

        timer = 0
        while timer < main.timeout:
            time.sleep(1)
            r = session.post(url_login10, json=sd22)
            data = r.json()
            if data['state'] == 'result':
                result_status = data['result']['status']
                if result_status == 'fail':
                    main.reply(sender, "Платеж не был завершен успешно. Попробуйте снова")
                elif result_status == 'success':
                    res = "Поздравляю! Платеж был проведен успешно, квитанция счёта Астана ЕРЦ " + \
                          last_sender_message['astanaErc_last_acc'] + " оплачена на сумму " + str(amount) + " тг.\n"
                    res += "Номер квитанции: " + str(payment_id)
                    res += ", она доступна на post.kz в разделе История платежей"
                    main.reply(sender, res)
                last_sender_message['payload'] = 'astanaErc.finished'
                main.mongo_update_record(last_sender_message)
                main.reply_typing_off(sender)
                main.reply_main_menu_buttons(sender)
                return "ok"
            timer += 1

        last_sender_message = main.mongo_get_by_sender(sender)
        if last_sender_message['payload'] == 'astanaErc.startPayment':
            strminutes = str(main.timeout // 60)
            main.reply(sender, "Прошло больше " + strminutes + " минут: платеж отменяется")
            main.reply_typing_off(sender)
            main.reply_main_menu_buttons(sender)
            last_sender_message['payload'] = 'mainMenu'
            main.mongo_update_record(last_sender_message)
        return "time exceed"

    except Exception as e:
        main.reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        main.reply_typing_off(sender)
        main.reply_main_menu_buttons(sender)
        logging.error(helper.PrintException())
        return "fail"