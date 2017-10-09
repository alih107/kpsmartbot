import requests
import logging
import time

import main
import helper
import constants

fb_url = main.fb_url
hint_main_menu = main.hint_main_menu
url = constants.url
x_channel_id = constants.x_channel_id
portal_id = constants.portal_id
portal_id_2 = constants.portal_id_2
timeout = main.timeout

def reply_addcard_entercard(sender, last_sender_message):
    cards = main.get_cards_json(sender, last_sender_message)
    if len(cards) > 0:
        res = 'Список добавленных карт:\n'
        for card in cards:
            if card['state'] != 'REGISTERED':
                continue
            card_title = card['title']
            if len(card_title) > 20:
                card_title = card['brand'] + ' *' + card['alias']
            res += card_title + '\n'
        res += '\nЕсли Вы хотите добавить карту, введите 16ти-значный номер карты'
        main.reply(sender, res)
    else:
        main.reply(sender, 'Чтобы добавить карту, введите 16ти-значный номер карты')

def reply_addcard_checkcard(sender, message, last_sender_message):
    message = message.replace(' ', '')
    if len(message) != 16:
        main.reply(sender, "Вы ввели не все 16 цифр карты, попробуйте ещё раз")
        return "addcard.again"
    if not helper.isAllDigits(message):
        main.reply(sender, "Некоторые введенные Вами цифры не являются цифрами, попробуйте ещё раз")
        return "addcard.again"
    last_sender_message['addcard_cardnumber'] = message
    last_sender_message['payload'] = 'addcard.expiredate'
    main.mongo_update_record(last_sender_message)
    main.reply(sender, "Введите месяц и год срока действия карты (например, 0418)\n" + hint_main_menu)

def reply_addcard_checkexpiredate(sender, message, last_sender_message):
    message = message.replace(' ', '')
    message = message.replace('.', '')
    message = message.replace('/', '')
    if len(message) != 4:
        main.reply(sender, "Вы должны ввести 4 цифры (2 на месяц, 2 на год), попробуйте ещё раз")
        return "addcard.expiredateagain"
    if not helper.isAllDigits(message):
        main.reply(sender, "Некоторые введенные Вами цифры не являются цифрами, попробуйте ещё раз")
        return "addcard.expiredateagain"
    last_sender_message['addcard_expiredate'] = message
    last_sender_message['payload'] = 'addcard.cardowner'
    main.mongo_update_record(last_sender_message)
    main.reply(sender, "Введите имя и фамилию на карте латинскими буквами\n" + hint_main_menu)

def reply_addcard_checkcardowner(sender, message, last_sender_message):
    last_sender_message['addcard_cardowner'] = message
    res = 'Проверьте данные:\n'
    res += 'Номер карты: ' + helper.insert_4_spaces(last_sender_message['addcard_cardnumber']) + '\n'
    res += 'Срок действия: ' + last_sender_message['addcard_expiredate'][:2] + '/' + \
                              last_sender_message['addcard_expiredate'][2:] + '\n'
    res += 'Имя на карте: ' + last_sender_message['addcard_cardowner'] + '\n'
    res += '\nЕсли всё верно, введите трехзначный код CSC/CVV2 на обратной стороне карты, чтобы добавить эту карту'
    last_sender_message['payload'] = 'addcard.csc'
    main.mongo_update_record(last_sender_message)
    main.reply(sender, res)

def reply_addcard_startAdding(sender, message, last_sender_message):
    if not helper.check_csc(message):
        main.reply(sender, "Вы неправильно ввели трёхзначный код CSC/CVV2 на обратной стороне карты, введите заново")
        return "ok"
    main.reply(sender, "Идет обработка добавления карты...")
    main.reply_typing_on(sender)
    try:
        # 1 - авторизация на post.kz
        url_login = 'https://post.kz/mail-app/api/account/'
        headers = {"Authorization": "Basic " + last_sender_message['encodedLoginPass'],
                   'Content-Type': 'application/json'}

        # 2 - создаём токен
        session = requests.Session()
        r = session.get(url_login, headers=headers)
        mobileNumber = r.json()['mobileNumber']

        # 3 - инициируем start registration
        url_login2 = 'https://post.kz/mail-app/api/intervale/token'
        data = {"phone": mobileNumber}
        r = session.post(url_login2, json=data)
        token = r.json()['token']

        # 4 - передаём все данные карты для регистрации карты
        url_login3 = 'https://post.kz/mail-app/api/intervale/card/registration/start/' + token
        data = {"phone": mobileNumber, "returnUrl": "https://post.kz/static/return.html"}
        r = session.post(url_login3, json=data)

        # 4 - передаём все данные карты для регистрации карты
        url_login5 = 'https://openapi-entry.intervale.ru/api/v3/'+ portal_id_2 +'/card/registration/'
        url_login5 += token + '/card-page-submit?fallback=https%3A%2F%2Fpost.kz%2Fstatic%2Freturn.html'
        data = {'pan': last_sender_message['addcard_cardnumber'],
                'expiry': last_sender_message['addcard_expiredate'],
                'csc': message,
                'cardholder': last_sender_message['addcard_cardowner'].lower(),
                'pageType': 'reg'}
        r = session.post(url_login5, data=data)
        result = r.json()
        try:
            if result['error'] == 'ALREADY_REGISTERED':
                main.reply(sender, "Эта карта уже добавлена в вашем профиле на post.kz")
                main.reply_main_menu_buttons(sender)
                return "ALREADY_REGISTERED"
        except:
            pass

        # 5 - дергаём статус, вытаскиваем url для 3DSecure
        url_login4 = 'https://post.kz/mail-app/api/intervale/card/registration/status/' + token
        data = {"phone": mobileNumber}
        r = session.post(url_login4, json=data)
        d = r.json()
        if d['state'] == 'redirect':
            main.reply_send_redirect_url(sender, d['url'])
            time.sleep(9)
        if d['state'] == 'confirmation':
            message =  'Для подтверждения карты, введите сумму, блокированную на вашей карте.\n'
            message += 'Блокированную сумму можно узнать через интернет-банкинг или call-центр вашего банка.\n'
            message += 'Осталось попыток: 3'
            main.reply(sender, message)
            last_sender_message['token'] = token
            last_sender_message['mobileNumber'] = mobileNumber
            last_sender_message['payload'] = 'addcard.confirmation'
            main.mongo_update_record(last_sender_message)
            return "confirmation"

        timer = 0
        while timer < timeout:
            time.sleep(1)
            r = session.post(url_login4, json=data)
            d = r.json()
            if d['state'] == 'result':
                status = d['result']['status']
                if status == 'success':
                    res = "Поздравляю! Карта успешно добавлена!"
                    main.reply(sender, res)
                if status == 'fail':
                    main.reply(sender, "Карта не была добавлена. Попробуйте снова")
                last_sender_message['payload'] = 'addcard.finished'
                main.mongo_update_record(last_sender_message)
                main.reply_main_menu_buttons(sender)
                return "ok"

        last_sender_message = main.mongo_get_by_sender(sender)
        if last_sender_message['payload'] == 'addcard.csc':
            strminutes = str(timeout // 60)
            main.reply(sender, "Прошло больше " + strminutes + " минут: добавление карты отменяется")
            main.reply_main_menu_buttons(sender)
            last_sender_message['payload'] = 'mainMenu'
            main.mongo_update_record(last_sender_message)
        return "time exceed"

    except:
        logging.error(helper.PrintException())
        main.reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        main.reply_main_menu_buttons(sender)
        return "fail"

def card_registration_confirm(sender, message, last_sender_message):
    message = message.replace('.', '')
    message = message.replace(' ', '')
    session = main.get_authorized_session(last_sender_message['encodedLoginPass'])

    phone = last_sender_message['mobileNumber']
    token = last_sender_message['token']
    url_confirmation = 'https://post.kz/mail-app/api/intervale/card/registration/confirm/' + token
    data = {'blockedAmount': message, 'phone': phone}
    r = session.post(url_confirmation, json=data)
    d = r.json()
    if d['state'] == 'confirmation':
        main.reply(sender, "Вы ввели неправильную сумму, осталось " + str(d['attempts']) + " попытки. Введите сумму ещё раз")
        return "wrongamount"
    if d['state'] == 'result':
        status = d['result']['status']
        if status == 'success':
            res = "Поздравляю! Карта успешно добавлена!"
            main.reply(sender, res)
        if status == 'fail':
            main.reply(sender, "Карта не была добавлена. Попробуйте снова")
        last_sender_message['payload'] = 'addcard.finished'
        main.mongo_update_record(last_sender_message)
        main.reply_main_menu_buttons(sender)
        return "ok"
