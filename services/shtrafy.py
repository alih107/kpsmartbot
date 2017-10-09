import requests
import logging

import main
import helper

fb_url = main.fb_url
hint_main_menu = main.hint_main_menu
hint_main_menu2 = main.hint_main_menu2
gosnomer_text = """Введите номер авто и номер техпаспорта через пробел
Правильный формат запроса: [номер авто] [номер техпаспорта]
Пример: 123AAA01 AA00000000"""

def check_penalties_pdd(last_sender_message, data):
    message = data['data']
    result = ''
    try:
        session = main.get_authorized_session(last_sender_message['encodedLoginPass'])

        url_login = 'https://post.kz/mail-app/api/v2/subscriptions'
        r = session.post(url_login, json=data)
        data = r.json()
        status = data['responseInfo']['status']
        if status == 'FAILED':
            result = 'Штрафов по данным ' + message + ' не найдено\n'
        else:
            subscriptionId = str(r.json()['subscriptionData']['id'])
            url_login = 'https://post.kz/mail-app/api/v2/subscriptions/' + subscriptionId + '/invoices'
            invoiceData = session.get(url_login).json()['invoiceData']
            for fine in invoiceData:
                desc = fine['details'][0]['description']
                amount = str(fine['details'][0]['amount'])
                result += desc + ' - сумма ' + amount + ' тг\n\n'
    except:
        url_login = 'https://post.kz/mail-app/api/public/v2/invoices/create'
        r = requests.post(url_login, json=data)
        data = r.json()
        status = data['responseInfo']['status']
        if status == 'FAILED':
            result = 'Штрафов по данным ' + message + ' не найдено\n'
        else:
            invoiceData = data['invoiceData']
            desc = invoiceData['details'][0]['description']
            amount = str(invoiceData['details'][0]['amount'])
            result += desc + ' - сумма ' + amount + ' тг\n'
        result += '(Информация может быть неполной! Для полной информации авторизуйтесь в главном меню)'
    return result

def reply_pdd_shtrafy(sender):
    data_quick_replies = {
      "recipient": {"id": sender},
      "message": {
        "text": " Выберите способ просмотра штрафов ПДД:\n" + hint_main_menu2,
        "quick_replies": [
          {
            "content_type": "text",
            "title": "По ИИН",
            "payload": "4.IIN"
          },
          {
            "content_type": "text",
            "title": "Госномер, техпаспорт",
            "payload": "4.GosNomer"
          }
        ]
      }
    }
    requests.post(fb_url, json=data_quick_replies)

def reply_pdd_shtrafy_iin_enter(sender, last_sender_message):
    pddIINs = []
    try:
        pddIINs = last_sender_message['pddIINs']
    except:
        last_sender_message['pddIINs'] = []

    try:
        assert len(pddIINs) > 0
        buttons = []
        for iin in pddIINs:
            buttons.append({"content_type": "text", "payload": "pddIIN.last", "title": iin})
        buttons.append({"content_type": "text", "payload": "pddIIN.delete", "title": "Удалить ИИН"})
        data_quick_replies = {
            "recipient": {"id": sender},
            "message": {
                "text": "Выберите ИИН или введите его\n" + hint_main_menu,
                "quick_replies": buttons
            }
        }
        requests.post(fb_url, json=data_quick_replies)
    except:
        main.reply(sender, "Введите 12-ти значный ИИН\n" + hint_main_menu)
    last_sender_message['payload'] = '4.IIN'
    main.mongo_update_record(last_sender_message)

def reply_pdd_shtrafy_iin(sender, message, last_sender_message):
    main.reply_typing_on(sender)
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
        main.reply(sender, "Вы ввели неправильный ИИН, введите еще раз")
        return "again"
    url_login = 'https://post.kz/mail-app/api/public/transfer/loadName/' + message
    r = requests.get(url_login).json()
    try:
        name = r['name']
    except:
        main.reply(sender, "Такой ИИН не найден, введите еще раз")
        return "again"

    data = {'operatorId': 'pddIin', 'data': message}
    result = check_penalties_pdd(last_sender_message, data)
    try:
        if not "pddIINs" in last_sender_message:
            last_sender_message['pddIINs'] = []
        if not message in last_sender_message['pddIINs'] and len(last_sender_message['pddIINs']) < 10:
            last_sender_message['pddIINs'].append(message)
    except:
        logging.error(helper.PrintException())

    result += "(Выберите или введите другой ИИН, чтобы посмотреть штрафы ПДД, " \
              "либо нажмите (y) для перехода в главное меню)"
    reply_pdd_shtrafy_iin_quick_replies_with_delete(sender, last_sender_message['pddIINs'], result)
    main.mongo_update_record(last_sender_message)

def reply_pdd_shtrafy_iin_quick_replies_with_delete(sender, pddIINs, text):
    buttons = []
    for iin in pddIINs:
        buttons.append({"content_type": "text", "payload": "pddIIN.last", "title": iin})
    buttons.append({"content_type": "text", "payload": "pddIIN.delete", "title": "Удалить ИИН"})
    data_quick_replies = {
        "recipient": {"id": sender},
        "message": {
            "text": text,
            "quick_replies": buttons
        }
    }
    requests.post(fb_url, json=data_quick_replies)

def reply_pdd_shtrafy_iin_delete(sender, last_sender_message):
    pddIINs = last_sender_message['pddIINs']
    buttons = []
    for iin in pddIINs:
        buttons.append({"content_type": "text", "payload": "pddIIN.delete.number", "title": iin})

    data_quick_replies = {
        "recipient": {"id": sender},
        "message": {
            "text": "Выберите ИИН, чтобы его удалить",
            "quick_replies": buttons
        }
    }
    requests.post(fb_url, json=data_quick_replies)

def reply_pdd_shtrafy_iin_delete_iin(sender, text, last_sender_message):
    last_sender_message['pddIINs'].remove(text)
    main.reply(sender, "ИИН " + text + " успешно удалён")
    reply_pdd_shtrafy_iin_enter(sender, last_sender_message)
    last_sender_message['payload'] = '4.IIN'
    main.mongo_update_record(last_sender_message)

def reply_pdd_shtrafy_gosnomer_enter(sender, last_sender_message):
    pddGosnomers = []
    try:
        pddGosnomers = last_sender_message['pddGosnomers']
    except:
        last_sender_message['pddGosnomers'] = []

    try:
        assert len(pddGosnomers) > 0
        buttons = []
        for gn in pddGosnomers:
            buttons.append({"content_type": "text", "payload": "pddGosnomer.last", "title": gn})
        buttons.append({"content_type": "text", "payload": "pddGosnomer.delete", "title": "Удалить авто"})
        data_quick_replies = {
            "recipient": {"id": sender},
            "message": {
                "text": "Выберите номер авто/техпаспорт или введите из через пробел (пример: 123AAA01 AA00000000)\n" + hint_main_menu,
                "quick_replies": buttons
            }
        }
        requests.post(fb_url, json=data_quick_replies)
    except:
        main.reply(sender, gosnomer_text + "\n" + hint_main_menu)
    last_sender_message['payload'] = '4.GosNomer'
    main.mongo_update_record(last_sender_message)

def reply_pdd_shtrafy_gosnomer(sender, message, last_sender_message):
    main.reply_typing_on(sender)
    data = {'operatorId': 'pddVehicle', 'data': message.replace(' ', '/')}
    result = check_penalties_pdd(last_sender_message, data)
    try:
        if not "pddGosnomers" in last_sender_message:
            last_sender_message['pddGosnomers'] = []
        if not message in last_sender_message['pddGosnomers'] and len(last_sender_message['pddIINs']) < 10:
            last_sender_message['pddGosnomers'].append(message)
    except:
        logging.error(helper.PrintException())

    result += "(Выберите или введите другой номер авто/техпаспорт через пробел (пример: 123AAA01 AA00000000), " \
              "чтобы посмотреть штрафы ПДД, либо нажмите (y) для перехода в главное меню)"
    reply_pdd_shtrafy_gosnomer_quick_replies_with_delete(sender, last_sender_message['pddGosnomers'], result)
    main.mongo_update_record(last_sender_message)

def reply_pdd_shtrafy_gosnomer_quick_replies_with_delete(sender, pddGosnomers, text):
    buttons = []
    for gn in pddGosnomers:
        buttons.append({"content_type": "text", "payload": "pddGosnomer.last", "title": gn})
    buttons.append({"content_type": "text", "payload": "pddGosnomer.delete", "title": "Удалить авто"})
    data_quick_replies = {
        "recipient": {"id": sender},
        "message": {
            "text": text,
            "quick_replies": buttons
        }
    }
    requests.post(fb_url, json=data_quick_replies)

def reply_pdd_shtrafy_gosnomer_delete(sender, last_sender_message):
    pddGosnomers = last_sender_message['pddGosnomers']
    buttons = []
    for gn in pddGosnomers:
        buttons.append({"content_type": "text", "payload": "pddGosnomer.delete.number", "title": gn})

    data_quick_replies = {
        "recipient": {"id": sender},
        "message": {
            "text": "Выберите авто, чтобы его удалить",
            "quick_replies": buttons
        }
    }
    requests.post(fb_url, json=data_quick_replies)

def reply_pdd_shtrafy_gosnomer_delete_gosnomer(sender, text, last_sender_message):
    last_sender_message['pddGosnomers'].remove(text)
    main.reply(sender, "Авто " + text + " успешно удалён")
    reply_pdd_shtrafy_gosnomer_enter(sender, last_sender_message)
    last_sender_message['payload'] = '4.GosNomer'
    main.mongo_update_record(last_sender_message)