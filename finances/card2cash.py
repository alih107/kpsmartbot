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
timeout = main.timeout

def reply_card2cash_history(sender, last_sender_message):
    main.reply_typing_on(sender)
    if main.check_login(sender, last_sender_message):
        try:
            main.reply_typing_on(sender)

            url_history = url + portal_id + '/payment/?pageSize=30&pageNumber=0&result=success&portalType=web'
            headers = {'Content-Type': 'application/x-www-form-urlencoded',
                       'X-Channel-Id': x_channel_id,
                       'X-IV-Authorization': 'Identifier ' + last_sender_message['mobileNumber']}
            r = requests.get(url_history, headers=headers)
            history_items = r.json()['items']
            card2cash_items = []
            for h in history_items:
                if h['paymentId'] == 'MoneyTransfer_KazPost_Card2Cash':
                    amount = str(h['amount'] // 100)
                    card_title = h['src']['title'][-4:]
                    desc_length = 20 - 2 - len(amount) - 4  # 20 - button title limit, 2 - for > and :, 4 - last 4 digits
                    description = h['description'][:desc_length]
                    title = card_title + '>' + description + ':' + amount
                    item = {'title': title, 'token': h['token']}
                    card2cash_items.append(item)

            elements = []
            buttons = []
            count = 0
            if len(card2cash_items) == 0:
                main.reply(sender, 'Пожалуйста, инициируйте операцию по переводу на руки на портале transfer.post.kz\n'
                              'Данная функция предназначена только для повторных операций')
                return
            for i in card2cash_items:
                if count > 0 and count % 3 == 0:
                    elements.append({'title': 'Выберите перевод (Карта>Кому:Сумма)', 'buttons': buttons})
                    buttons = []
                buttons.append({"type": "postback", "title": i['title'], "payload": i['token']})
                count += 1
            elements.append({'title': 'Выберите перевод (Карта>Кому:Сумма)', 'buttons': buttons})
            data_items_buttons = {
                "recipient": {"id": sender},
                "message": {
                    "attachment": {
                        "type": "template",
                        "payload": {
                            "template_type": "generic",
                            "elements": elements
                        }
                    }
                }
            }
            requests.post(fb_url, json=data_items_buttons)
            last_sender_message['payload'] = 'card2cash'
            main.mongo_update_record(last_sender_message)
        except:
            logging.error(helper.PrintException())

def reply_card2cash_history_show(sender, last_sender_message, token):
    try:
        main.reply_typing_on(sender)
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'X-Channel-Id': x_channel_id,
                   'X-IV-Authorization': 'Identifier ' + last_sender_message['mobileNumber']}

        url_token_show = url + portal_id + '/payment/' + token
        r = requests.get(url_token_show, headers=headers)
        data = r.json()
        result = "Проверьте введённые данные:" \
                "\nКарта: " + data['src']['title'] + \
                "\nСумма: " + str(data['amount'] // 100) + \
                "\nКомиссия: " + str(data['commission'] // 100) + \
                "\nИтого: " + str((int(data['amount'])+int(data['commission'])) // 100) + \
                "\nФИО получателя: " + data['params']['rcpnLastname'] + " " + data['params']['rcpnName'] + \
                "\nАдрес получателя: " + data['params']['rcpnAddr'] + \
                "\nНомер телефона получателя: " + data['params']['rcpnPhone'] + \
                "\nКодовое слово: " + data['params']['codeWord'] + \
                "\n\nЧтобы подтвердить перевод, введите трехзначный код CSC/CVV2 на обратной стороне карты"
        main.reply(sender, result)
        last_sender_message['card2cash_token'] = token
        main.mongo_update_record(last_sender_message)
    except:
        main.reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        logging.error(helper.PrintException())

def reply_card2cash_history_startPayment(sender, message, last_sender_message):
    if not helper.check_csc(message):
        main.reply(sender, "Вы неправильно ввели трёхзначный код CSC/CVV2 на обратной стороне карты, введите заново")
        return "ok"
    main.reply(sender, "Идёт обработка перевода, подождите 1-2 минуты...")
    main.reply_typing_on(sender)
    try:
        token = last_sender_message['card2cash_token']
        session = requests.Session()
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'X-Channel-Id': x_channel_id,
                   'X-IV-Authorization': 'Identifier ' + last_sender_message['mobileNumber']}

        url_token_show = url + portal_id + '/payment/' + token
        r = session.get(url_token_show, headers=headers)
        data = r.json()

        url_token = url + portal_id + '/token'
        r = session.post(url_token, headers=headers)
        new_token = r.json()['token']

        data1 = {
            'paymentId': "MoneyTransfer_KazPost_Card2Cash",
            'returnUrl': 'https://post.kz/static/return.html',
            'src.type': 'card_id',
            'src.cardholder': 'NAME',
            'src.cardId': data['src']['cardId'],
            'src.csc': message,
            'src.addToProfile': 'true',
            'amount': str(data['amount']),
            'commission': str(data['commission']),
            'total': str(data['amount'] + data['commission']),
            'currency': data['currency'],
            'params.transfType': data['params']['transfType'],
            'params.transfPurpose': data['params']['transfPurpose'],
            'params.cliResident': data['params']['cliResident'],
            'params.cliTaxcode': data['params']['cliTaxcode'],
            'params.cliLastname': data['params']['cliLastname'],
            'params.cliName': data['params']['cliName'],
            'params.cliAddr': data['params']['cliAddr'],
            'params.cliPhone': data['params']['cliPhone'],
            'params.passportType': data['params']['passportType'],
            'params.passportNum': data['params']['passportNum'],
            'params.passportDate': data['params']['passportDate'],
            'params.passportOrg': data['params']['passportOrg'],
            'params.rcpnLastname': data['params']['rcpnLastname'],
            'params.rcpnName': data['params']['rcpnName'],
            'params.rcpnAddr': data['params']['rcpnAddr'],
            'params.rcpnPhone': data['params']['rcpnPhone'],
            'params.codeWord': data['params']['codeWord'],
        }
        url_start = url + portal_id + '/payment/' + new_token + '/start'
        requests.post(url_start,                                                                                                                                                                                        data1, headers=headers)

        url_status = url + portal_id + '/payment/' + new_token
        timer = 0
        urlSent = False
        main.reply_typing_on(sender)
        while timer < timeout:
            if urlSent:
                time.sleep(1)
            r = session.post(url_status, headers=headers).json()
            if r['state'] == 'redirect' and not urlSent:
                main.reply_send_redirect_url(sender, r['url'])
                urlSent = True
            if r['state'] == 'result':
                if r['result']['status'] == 'fail':
                    main.reply(sender, "Перевод не был завершен успешно. Попробуйте снова")
                if r['result']['status'] == 'suspended':
                    main.reply(sender, "Возникла проблема на стороне банка, перевод не был осуществлён. Попробуйте позже")
                if r['result']['status'] == 'success':
                    res = "Поздравляю! Перевод был проведен успешно!"
                    res += "\nВнимание! Сообщите контрольный номер перевода и кодовое слово получателю перевода"
                    res += "\nКонтрольный номер перевода: " + r['result']['transferCode']
                    res += "\nКонтрольное слово: " + data['params']['codeWord']
                    main.reply(sender, res)
                main.reply_main_menu_buttons(sender, last_sender_message)
                return
            timer += 1

        last_sender_message = main.mongo_get_by_sender(sender)
        if last_sender_message['payload'] == 'card2cash.show':
            strminutes = str(timeout // 60)
            main.reply(sender, "Прошло больше " + strminutes + " минут: перевод отменяется")
            main.reply_main_menu_buttons(sender, last_sender_message)
        return "time exceed"
    except:
        main.reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        logging.error(helper.PrintException())
