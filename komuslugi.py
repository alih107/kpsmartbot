import main
import helper
import requests
import constants
import logging
fb_url = main.fb_url

def get_komuslugi(last_sender_message, data):
    message = data['data']
    result = ''
    session = requests.Session()
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
            subscriptionId = str(r.json()['subscriptionData']['id'])
            url_login = 'https://post.kz/mail-app/api/v2/subscriptions/' + subscriptionId + '/invoices'
            data = session.get(url_login).json()
            logging.info(data)
            invoiceData = data['invoiceData'][0]
            result = 'Информация по лицевому счёту ' + message + '\n'
            result += invoiceData['description'] + '\n\n'
            for i in invoiceData['details']:
                desc = i['description']
                amount = i['amount']
                amount_str = ', сумма ' + str(amount) + ' тг'
                debt = i['debt']
                debt_str = ''
                if debt > 0:
                    debt_str = ', долг ' + str(debt) + ' тг'
                result += desc + debt_str + amount_str + '\n'
    except:
        main.reply(last_sender_message['sender'], "Произошла непредвиденная ошибка, попробуйте позднее")
        logging.error(helper.PrintException())
        return 'error'
    return result

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
        result = get_komuslugi(last_sender_message, data)
        if result == 'error':
            return
        if not "astanaErc_accounts" in last_sender_message:
            last_sender_message['astanaErc_accounts'] = []
        if not message in last_sender_message['astanaErc_accounts'] and len(last_sender_message['astanaErc_accounts']) < 10:
            last_sender_message['astanaErc_accounts'].append(message)

        reply_astanaErc_quick_replies_with_delete(sender, last_sender_message['astanaErc_accounts'], result)
        last_sender_message['astanaErc_last_acc'] = message
        main.mongo_update_record(last_sender_message)
    except:
        logging.error(helper.PrintException())

def reply_astanaErc_quick_replies_with_delete(sender, astanaErc_accounts, text):
    main.reply(sender, text)
    data_text = "(Вы можете оплатить квитанцию, выбрать или ввести номер лицевого счёта Астана ЕРЦ, чтобы посмотреть " \
                "квитанции, либо нажать (y) для перехода в главное меню)"
    buttons = []
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
    r = requests.post(fb_url, json=data_quick_replies)

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