import requests
import logging
import time

import main
import helper

fb_url = main.fb_url
hint_main_menu = main.hint_main_menu
operators_dict = {'Tele2': 'tele2Wf', 'Beeline': 'beelineWf', 'Activ': 'activWf', 'Kcell': 'kcellWf'}
timeout = main.timeout

def reply_mobile_enter_number(sender, last_sender_message):
    if main.check_login(sender, last_sender_message):
        try:
            phonesToRefill = last_sender_message['phonesToRefill']
            assert len(phonesToRefill) > 0
            buttons = []
            for phone in phonesToRefill:
                buttons.append({"content_type": "text", "payload": "mobile.last", "title": phone})

            buttons.append({"content_type": "text", "payload": "mobile.delete", "title": "Удалить номер"})

            data_quick_replies = {
                "recipient": {"id": sender},
                "message": {
                    "text": "Выберите номер телефона или введите его\n" + hint_main_menu,
                    "quick_replies": buttons
                }
            }
            requests.post(fb_url, json=data_quick_replies)
        except:
            main.reply(sender, "Введите номер телефона\n" + hint_main_menu)
        last_sender_message['payload'] = 'balance'
        main.mongo_update_record(last_sender_message)


def reply_mobile_check_number(sender, message, last_sender_message):
    url_login = 'https://post.kz/mail-app/public/check/operator'
    message = message.replace(' ', '')
    message = message[-10:]
    r = requests.post(url_login, json={"phone": message})
    operator = r.json()['operator']

    if operator == 'error':
        main.reply(sender, "Вы ввели неправильный номер телефона. Попробуйте еще раз")
        return "error"

    operator = operator[:-2].title()
    minAmount = 0
    if operator == 'Tele2' or operator == 'Beeline':
        minAmount = 100
    elif operator == 'Activ' or operator == 'Kcell':
        minAmount = 200
    else:
        main.reply(sender, "Оператор " + operator + " сейчас не поддерживается. Введите другой номер, пожалуйста.")
        return "other operator"

    last_sender_message['mobileOperator'] = operator
    last_sender_message['payload'] = 'mobile.amount'
    last_sender_message['phoneToRefill'] = message

    try:
        if not "phonesToRefill" in last_sender_message:
            last_sender_message['phonesToRefill'] = []
        if not message in last_sender_message['phonesToRefill'] and len(last_sender_message['phonesToRefill']) < 10:
            last_sender_message['phonesToRefill'].append(message)
    except:
        logging.error(helper.PrintException())

    last_sender_message['minAmount'] = minAmount
    main.mongo_update_record(last_sender_message)

    title = "Оператор номера: " + operator + "\nВведите сумму пополнения баланса (не менее " + str(minAmount) + " тг)"
    main.reply(sender, title)


def reply_mobile_delete(sender, last_sender_message):
    phonesToRefill = last_sender_message['phonesToRefill']
    buttons = []
    for phone in phonesToRefill:
        buttons.append({"content_type": "text", "payload": "mobile.delete.phone", "title": phone})

    data_quick_replies = {
        "recipient": {
            "id": sender
        },
        "message": {
            "text": "Выберите номер телефона, чтобы его удалить",
            "quick_replies": buttons
        }
    }
    requests.post(fb_url, json=data_quick_replies)


def reply_mobile_delete_phone(sender, text, last_sender_message):
    last_sender_message['phonesToRefill'].remove(text)
    main.reply(sender, "Номер " + text + " успешно удалён")
    reply_mobile_enter_number(sender, last_sender_message)
    last_sender_message['payload'] = 'balance'
    main.mongo_update_record(last_sender_message)


def reply_mobile_amount(sender, message, last_sender_message):
    amount = 0
    minAmount = last_sender_message['minAmount']
    try:
        amount = int(message)
    except:
        main.reply(sender, "Вы неправильно ввели сумму пополнения баланса. Введите сумму заново")
        return "again"

    if amount < minAmount:
        main.reply(sender, "Сумма пополнения баланса должна быть не менее " + str(minAmount) + " тг. Введите сумму заново")
        return "again"

    main.reply_display_cards(sender, last_sender_message)
    operator = last_sender_message['mobileOperator']
    commission = 0
    if operator == 'Activ' or operator == 'Kcell':
        commission = amount / 10
        if commission > 70:
            commission = 70
    elif operator == 'Tele2' or operator == 'Beeline':
        commission = 50
    last_sender_message['commission'] = commission
    last_sender_message['payload'] = 'mobile.chooseCard'
    last_sender_message['amount'] = amount
    main.mongo_update_record(last_sender_message)


def reply_mobile_csc(sender, payload, last_sender_message):
    amount = last_sender_message['amount']
    commission = last_sender_message['commission']
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

    main.reply(sender, message)


def reply_mobile_startPayment(sender, message, last_sender_message):
    main.reply(sender, "Идет обработка платежа...")
    main.reply_typing_on(sender)
    # 1 - авторизация на post.kz
    try:
        url_login = 'https://post.kz/mail-app/api/account/'
        headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'],
                   'Content-Type': 'application/json'}

        session = requests.Session()
        r = session.get(url_login, headers=headers)

        # 2 - вызов createSubscription() из PaymentAPI
        url_login2 = 'https://post.kz/mail-app/api/v2/subscriptions'
        login = last_sender_message['login']
        operatorId = last_sender_message['mobileOperator']
        phoneToRefill = last_sender_message['phoneToRefill']
        amount = last_sender_message['amount']
        sd2 = {"id": "", "login": login, "operatorId": operators_dict[operatorId],
               "data": phoneToRefill, "name": "", "invoiceIds": ""}
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
        sd2 = {"blockedAmount": "", "phone": mobileNumber, "paymentId": "", "returnUrl": "", "transferId": ""}
        r = session.post(url_login4, json=sd2)
        token = r.json()['token']

        body['token'] = token
        body['invoiceId'] = invoiceId
        body['systemId'] = 'mobile'
        body['details'][0]['amount'] = amount
        body['details'][0]['commission'] = last_sender_message['commission']
        # print ('#############################################')
        # print (body)

        # 5 - вызов createPayment()
        url_login5 = 'https://post.kz/mail-app/api/v2/payments/create?device=mobile'
        r = session.post(url_login5, json=body)
        payment_id = r.json()['paymentData']['id']
        # print ('#############################################')
        # print (r.json())

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
            main.reply_send_redirect_url(sender, data['url'])
            time.sleep(9)

        timer = 0
        while timer < timeout:
            time.sleep(1)
            r = session.post(url_login10, json=sd22)
            data = r.json()
            try:
                result_status = data['result']['status']
                if result_status == 'fail':
                    main.reply(sender, "Платеж не был завершен успешно. Попробуйте снова")
                elif result_status == 'success':
                    res = "Поздравляю! Платеж был проведен успешно, номер " + phoneToRefill + " пополнен на сумму " + str(
                        amount) + " тг.\n"
                    res += "Номер квитанции: " + str(payment_id)
                    res += ", она доступна в профиле post.kz в разделе История платежей"
                    main.reply(sender, res)
                last_sender_message['payload'] = 'mobile.finished'
                main.mongo_update_record(last_sender_message)
                main.reply_main_menu_buttons(sender)
                return "ok"
            except Exception as e:
                pass
            timer += 1

        last_sender_message = main.mongo_get_by_sender(sender)
        if last_sender_message['payload'] == 'mobile.startPayment':
            strminutes = str(timeout // 60)
            main.reply(sender, "Прошло больше " + strminutes + " минут: платеж отменяется")
            main.reply_main_menu_buttons(sender)
            last_sender_message['payload'] = 'mainMenu'
            main.mongo_update_record(last_sender_message)
        return "time exceed"
    except Exception:
        logging.error(helper.PrintException())
        main.reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        main.reply_main_menu_buttons(sender)
        return "fail"