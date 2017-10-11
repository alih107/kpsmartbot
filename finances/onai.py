import requests
import logging
import time

import main
import helper

fb_url = main.fb_url
hint_main_menu = main.hint_main_menu
timeout = main.timeout

def reply_onai(sender, message, last_sender_message, is_voice=None):
    added_text = ''
    if is_voice:
        added_text = 'Вы продиктовали номер ' + helper.insert_spaces_onai(message) + '.\n'
    url_login = 'https://post.kz/mail-app/api/public/v2/invoices/create'
    message = message.replace(' ', '')
    r = requests.post(url_login, json={"operatorId": "onai", "data": message})
    if r.status_code == 404:
        main.reply(sender, added_text + "Вы ввели неправильный номер карты Онай, введите еще раз")
        return "wrong onai number"

    if is_voice:
        buttons = [{"content_type": "text", "payload": "onai.again", "title": "Ввести номер заново"}]
        data_quick_replies = {
            "recipient": {"id": sender},
            "message": {
                "text": added_text + "Введите сумму пополнения баланса (не менее 100 тг, комиссия 0 тг)",
                "quick_replies": buttons
            }
        }
        requests.post(fb_url, json=data_quick_replies)
    else:
        main.reply(sender, added_text + "Введите сумму пополнения баланса (не менее 100 тг, комиссия 0 тг)")
    last_sender_message['onaiToRefill'] = message
    try:
        if not "onaisToRefill" in last_sender_message:
            last_sender_message['onaisToRefill'] = []
        if not message in last_sender_message['onaisToRefill'] and len(last_sender_message['onaisToRefill']) < 10:
            last_sender_message['onaisToRefill'].append(message)
    except:
        logging.error(helper.PrintException())

    last_sender_message['payload'] = 'onai.amount'
    main.mongo_update_record(last_sender_message)


def reply_onai_enter_number(sender, last_sender_message):
    try:
        onaisToRefill = last_sender_message['onaisToRefill']
        assert len(onaisToRefill) > 0
        buttons = []
        for onai in onaisToRefill:
            onai = helper.insert_space_onai(onai)
            buttons.append({"content_type": "text", "payload": "onai.last", "title": onai})
        buttons.append({"content_type": "text", "payload": "onai.delete", "title": "Удалить карту"})
        data_quick_replies = {
            "recipient": {"id": sender},
            "message": {
                "text": "Выберите карту Онай или введите его\n" + hint_main_menu,
                "quick_replies": buttons
            }
        }
        requests.post(fb_url, json=data_quick_replies)
    except:
        main.reply(sender, "Введите 19ти-значный номер карты Онай\n" + hint_main_menu)


def reply_onai_delete(sender, last_sender_message):
    onaisToRefill = last_sender_message['onaisToRefill']
    buttons = []
    for onai in onaisToRefill:
        onai = helper.insert_space_onai(onai)
        buttons.append({"content_type": "text", "payload": "onai.delete.phone", "title": onai})

    data_quick_replies = {
        "recipient": {
            "id": sender
        },
        "message": {
            "text": "Выберите карту Онай, чтобы её удалить",
            "quick_replies": buttons
        }
    }
    requests.post(fb_url, json=data_quick_replies)


def reply_onai_delete_phone(sender, text, last_sender_message):
    last_sender_message['onaisToRefill'].remove(text.replace(' ', ''))
    main.reply(sender, "Карта Онай " + text + " успешно удалёна")
    reply_onai_enter_number(sender, last_sender_message)
    last_sender_message['payload'] = 'onai'
    main.mongo_update_record(last_sender_message)


def reply_onai_amount(sender, message, last_sender_message, is_voice=None):
    added_text = ''
    if is_voice:
        added_text = 'Вы продиктовали сумму ' + message + '.\n'
    amount = 0
    minAmount = 100
    try:
        amount = int(message)
    except:
        main.reply(sender, added_text + "Вы неправильно ввели сумму пополнения баланса. Введите сумму заново")
        return "again"

    if amount < minAmount:
        main.reply(sender, added_text + "Сумма пополнения баланса должна быть не менее " + str(minAmount) + " тг. Введите сумму заново")
        return "again"

    if is_voice:
        main.reply_just_text(sender, added_text)
    last_sender_message['payload'] = 'onai.chooseCard'
    last_sender_message['amount'] = amount
    main.mongo_update_record(last_sender_message)
    main.reply_display_cards(sender, last_sender_message)


def reply_onai_csc(sender, payload, last_sender_message):
    amount = last_sender_message['amount']
    onaiToRefill = last_sender_message['onaiToRefill']
    chosenCard = last_sender_message[payload]

    message = "Вы ввели:\n"
    message += "Номер карты Онай: " + onaiToRefill + '\n'
    message += "Сумма: " + str(amount) + " тг\n"
    message += "Карта: " + chosenCard + '\n\n'
    message += "Если всё верно, введите трехзначный код CSC/CVV2 на обратной стороне карты"

    main.reply(sender, message)


def reply_onai_startPayment(sender, message, last_sender_message):
    if not helper.check_csc(message):
        main.reply(sender, "Вы неправильно ввели трёхзначный код CSC/CVV2 на обратной стороне карты, введите заново")
        return "ok"
    main.reply(sender, "Идет обработка платежа...")
    main.reply_typing_on(sender)
    # 1 - авторизация на post.kz
    try:
        session = main.get_authorized_session(last_sender_message['encodedLoginPass'])

        # 2 - вызов createSubscription() из PaymentAPI
        url_login2 = 'https://post.kz/mail-app/api/v2/subscriptions'
        login = last_sender_message['login']
        operatorId = 'onai'
        onaiToRefill = last_sender_message['onaiToRefill']
        amount = last_sender_message['amount']
        sd2 = {"id": "", "login": login, "operatorId": operatorId, "data": onaiToRefill, "name": "", "invoiceIds": ""}
        r = session.post(url_login2, json=sd2)
        data = r.json()

        subscriptionId = str(data['subscriptionData']['id'])
        invoiceId = data['subscriptionData']['invoiceIds'][0]

        # 3 - вызов getInvoices() из PaymentAPI
        url_login3 = 'https://post.kz/mail-app/api/v2/subscriptions/' + subscriptionId + '/invoices'
        r = session.get(url_login3)
        body = r.json()['invoiceData'][0]

        # 4 - вызов getToken()
        mobileNumber = last_sender_message['mobileNumber']
        token = main.get_token_postkz(session, mobileNumber)

        body['token'] = token
        body['invoiceId'] = invoiceId
        body['systemId'] = 'POSTKZ'
        body['details'][0]['amount'] = amount
        body['details'][0]['commission'] = 0

        # 5 - вызов createPayment()
        url_login5 = 'https://post.kz/mail-app/api/v2/payments/create'
        r = session.post(url_login5, json=body)
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
        while timer < timeout:
            time.sleep(1)
            r = session.post(url_login10, json=sd22)
            data = r.json()
            if data['state'] == 'result':
                result_status = data['result']['status']
                if result_status == 'fail':
                    main.reply(sender, "Платеж не был завершен успешно. Попробуйте снова")
                elif result_status == 'success':
                    res = "Поздравляю! Платеж был проведен успешно, карта Онай " + onaiToRefill + " пополнена на сумму " + str(
                        amount) + " тг.\n"
                    res += "Номер квитанции: " + str(payment_id)
                    res += ", она доступна на post.kz в разделе История платежей"
                    main.reply(sender, res)
                main.reply_main_menu_buttons(sender, last_sender_message)
                return "ok"
            timer += 1

        last_sender_message = main.mongo_get_by_sender(sender)
        if last_sender_message['payload'] == 'onai.startPayment':
            strminutes = str(timeout // 60)
            main.reply(sender, "Прошло больше " + strminutes + " минут: платеж отменяется")
            main.reply_main_menu_buttons(sender, last_sender_message)
        return "time exceed"
    except:
        main.reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        main.reply_main_menu_buttons(sender, last_sender_message)
        logging.error(helper.PrintException())
        return "fail"
