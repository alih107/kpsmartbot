import requests
import base64
import os
import pymongo
import datetime
import logging
import json
import constants
import helper

client = pymongo.MongoClient()
db = client.kpsmartbot_db
collection_messages = db.messages
url = constants.url
x_channel_id = constants.x_channel_id
portal_id = constants.portal_id
portal_id_2 = constants.portal_id_2
ACCESS_TOKEN = constants.ACCESS_TOKEN
fb_url = "https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN
api_key = constants.api_key

hint_main_menu = "(для перехода в главное меню нажмите кнопку (y) "
hint_main_menu2 = "(Нажмите (y) для перехода в главное меню)"
timeout = 300
to_find_dict = {'nearest.postamats': 'ближайший постамат',
                'nearest.offices': 'ближайшее отделение',
                'nearest.atms': 'ближайший банкомат'}

url_mobile_payments = 'https://post.kz/finance/payment/mobile'

def get_authorized_session(encodedLoginPass):
    url_login = 'https://post.kz/mail-app/api/account/'
    headers = {"Authorization": "Basic " + encodedLoginPass, 'Content-Type': 'application/json'}
    session = requests.Session()
    session.get(url_login, headers=headers)
    return session

def get_token_postkz(session, mobileNumber):
    url_login4 = 'https://post.kz/mail-app/api/intervale/token'
    sd2 = {"blockedAmount": "", "phone": mobileNumber, "paymentId": "", "returnUrl": "", "transferId": ""}
    r = session.post(url_login4, json=sd2)
    return r.json()['token']

def get_cards_json(sender, last_sender_message):
    session = get_authorized_session(last_sender_message['encodedLoginPass'])

    url_login6 = 'https://post.kz/mail-app/api/intervale/card?device=mobile'
    sd2 = {"blockedAmount": "", "phone": last_sender_message['mobileNumber'], "paymentId": "", "returnUrl": "",
           "transferId": ""}
    r = session.post(url_login6, json=sd2)
    if r.status_code != 200:
        reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        reply_main_menu_buttons(sender)
    return r.json()

def mongo_update_record(last_sender_message):
    collection_messages.update_one({'sender': last_sender_message['sender']},
                                   {"$set": last_sender_message}, upsert=False)

def mongo_get_by_sender(sender):
    return collection_messages.find_one({"sender": sender})

def check_login(sender, last_sender_message):
    if last_sender_message['encodedLoginPass'] == None:
        reply(sender, "Требуется авторизация, пожалуйста, отправьте логин и пароль профиля на post.kz через "
                      "пробел. Если у вас нет аккаунта, то зарегистрируйтесь в https://post.kz/register")
        last_sender_message['payload'] = 'auth'
        mongo_update_record(last_sender_message)
        return False
    return True

def send_voice(sender, msg):
    try:
        ya_url = 'https://tts.voicetech.yandex.net/generate?key=' + api_key + '&text='
        ya_url += msg
        ya_url += '&format=mp3&quality=hi&lang=ru-RU&speaker=omazh&speed=1.0&emotion=good'
        r = requests.get(ya_url)
        voice_file = 'ya_' + sender + '.mp3'
        with open(voice_file, "wb") as o:
            o.write(r.content)
        data = {
            'recipient': '{id:' + sender + '}',
            'message': '{"attachment":{"type":"audio", "payload":{}}}'
        }
        files = {'filedata': (voice_file, open(voice_file, "rb"), 'audio/mp3')}
        requests.post(fb_url, data=data, files=files)
        try:
            os.remove(voice_file)
        except:
            pass
    except:
        logging.error(helper.PrintException())

def reply(sender, msg):
    if len(msg) > 640:
        result = ''
        msg_parts = msg.split('\n')
        for part in msg_parts:
            if len(result + part + '\n') > 640:
                data = {"recipient": {"id": sender}, "message": {"text": result}}
                requests.post(fb_url, json=data)
                result = part + '\n'
            else:
                result += part + '\n'
        msg = result
    data = {"recipient": {"id": sender}, "message": {"text": msg}}
    requests.post(fb_url, json=data)
    last_sender_message = collection_messages.find_one({"sender": sender})
    if last_sender_message['sendVoice']:
        send_voice(sender, msg)

def reply_just_text(sender, msg):
    data = {"recipient": {"id": sender}, "message": {"text": msg}}
    requests.post(fb_url, json=data)

def reply_gif_desktop(sender):
    data = {
        "recipient": {"id": sender},
        "message": {"attachment": {"type": "image", "payload":
                    {'url': 'https://thumbs.gfycat.com/TastyOrderlyCod-size_restricted.gif'}}}
    }
    requests.post(fb_url, json=data)

def reply_gif_mobile(sender):
    data = {
        "recipient": {"id": sender},
        "message": {"attachment": {"type": "image", "payload":
                    {'url': 'https://thumbs.gfycat.com/ThickHappyHalicore-size_restricted.gif'}}}
    }
    requests.post(fb_url, json=data)

def reply_typing_on(sender):
    data = {"recipient": {"id": sender}, "sender_action": "typing_on"}
    requests.post(fb_url, json=data)

def reply_typing_off(sender):
    data = {"recipient": {"id": sender}, "sender_action": "typing_off"}
    requests.post(fb_url, json=data)

def reply_main_menu_buttons(sender):
    data_main_menu_buttons = {
        "recipient": {"id": sender},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": "Главное меню",
                            "buttons": [
                                {
                                    "type": "postback",
                                    "title": "📲 Пополнение баланса",
                                    "payload": "balance"
                                },
                                {
                                    "type": "postback",
                                    "title": "🔍 Отслеживание",
                                    "payload": "tracking"
                                },
                                {
                                    "type": "postback",
                                    "title": "📍Ближайшие отделения",
                                    "payload": "nearest"
                                }
                            ]
                        },
                        {
                            "title": "Доп. услуги",
                            "buttons": [
                                {
                                    "type": "postback",
                                    "title": "💲 Курсы валют",
                                    "payload": "10.kursy"
                                },
                                {
                                    "type": "postback",
                                    "title": "🚗 Штрафы ПДД",
                                    "payload": "shtrafy"
                                },
                                {
                                    "type": "postback",
                                    "title": "📃 Оплата ком.услуг",
                                    "payload": "komuslugi"
                                }
                            ]
                        },
                        {
                            "title": "Платежи",
                            "buttons": [
                                {
                                    "type": "postback",
                                    "title": "💳 Перевод на карту",
                                    "payload": "card2card"
                                },
                                {
                                    "type": "postback",
                                    "title": "💸 Перевод на руки",
                                    "payload": "card2cash"
                                },
                                {
                                    "type": "postback",
                                    "title": "🚌 Пополнение Онай",
                                    "payload": "onai"
                                },
                            ]
                        },
                        {
                            "title": "Прочие услуги",
                            "buttons": [
                                {
                                    "type": "web_url",
                                    "title": "⚖️ Cудебные штрафы",
                                    "url": "https://post.kz/finance/payment/fines",
                                    "webview_height_ratio": "full"
                                },
                                {
                                    "type": "postback",
                                    "title": "📁 Прочее",
                                    "payload": "misc"
                                },
                                {
                                    "type": "postback",
                                    "title": "✖ Отключить бота",
                                    "payload": "disable.bot"
                                }
                            ]
                        },
                        {
                            "title": "Профиль на post.kz",
                            "buttons": [
                                {
                                    "type": "postback",
                                    "title": "Авторизация",
                                    "payload": "auth"
                                },
                                {
                                    "type": "postback",
                                    "title": "Мои карты",
                                    "payload": "addcard"
                                },
                                {
                                    "type": "postback",
                                    "title": "Удаление авторизации",
                                    "payload": "auth.delete"
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }
    requests.post(fb_url, json=data_main_menu_buttons)

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
    if r.status_code != 200:
        reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        reply_main_menu_buttons(sender)
        return "again"

    title = "Выберите карту"
    cards_group = []
    cards_array = []
    index = 0
    if len(cards) == 0:
        reply(sender, "У вас отсутствуют добавленные карты в профиле post.kz. "
                      "Чтобы добавить, введите 16ти-значный номер карты")
        last_sender_message['payload'] = 'addcard'
        mongo_update_record(last_sender_message)
        return
    for card in cards:
        if card['state'] != 'REGISTERED':
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
        "recipient": {"id": sender},
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
    requests.post(fb_url, json=data_cards)
    mongo_update_record(last_sender_message)

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
    requests.post(fb_url, json=data_url_button)
    reply_typing_off(sender)

def reply_currencies_kursy(sender):
    data = requests.get("https://post.kz/mail-app/info/remote/currencies/ops").json()
    result = "Курс валют на " + datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S') + " (время астанинское GMT +6)\n"
    result += "USD: " + data['usdBuy'] + " / " + data['usdSell'] + '\n'
    result += "EUR: " + data['eurBuy'] + " / " + data['eurSell'] + '\n'
    result += "RUB: " + data['rurBuy'] + " / " + data['rurSell'] + '\n'
    result += hint_main_menu
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
        mobile = '7' + profile_data['mobileNumber'][-10:]
        answer = "Вы успешно авторизованы! Добро пожаловать, " + profile_data['firstName'] + "!\n"
        answer += "В целях безопасности удалите сообщение с вашими логином и паролем"
        reply(sender, answer)
        last_sender_message['encodedLoginPass'] = encodedLoginPass
        last_sender_message['login'] = login
        last_sender_message['iin'] = iin
        last_sender_message['mobileNumber'] = mobile
        mongo_update_record(last_sender_message)
        reply_main_menu_buttons(sender)

def reply_misc(sender):
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
                    "type": "web_url",
                    "title": "📝 Работа в КазПочте",
                    "url": "https://post.kz/info/7/o-kompanii/item/273/vacancy",
                    "webview_height_ratio": "full"
                  },
                  {
                    "type": "web_url",
                    "title": "📜Проверить квитанцию",
                    "url": "https://post.kz/invoice",
                    "webview_height_ratio": "full"
                  },
                  {
                    "type": "web_url",
                    "title": "🏢 Посетить отделение",
                    "url": "https://post.kz/departments/list",
                    "webview_height_ratio": "full"
                  }
                ]
              }
            }
          }
    }
    requests.post(fb_url, json=data_misc_buttons)

def reply_has_cards(sender, last_sender_message):
    session = get_authorized_session(last_sender_message['encodedLoginPass'])
    
    url_login6 = 'https://post.kz/mail-app/api/intervale/card?device=mobile'
    sd2 = {"blockedAmount": "", "phone": last_sender_message['mobileNumber'], "paymentId": "",
           "returnUrl": "", "transferId": ""}
    r = session.post(url_login6, json=sd2)
    if r.status_code != 200:
        reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        reply_main_menu_buttons(sender)
        return False
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
    requests.post(fb_url, json=data_misc_buttons)

def reply_nearest_request_location(sender, payload):
    data_quick_replies = {
        "recipient": {
            "id": sender
        },
        "message": {
            "text": "Отправьте своё местоположение, чтобы найти " + to_find_dict[payload],
            "quick_replies": [
                {
                    "content_type": "location",
                }
            ]
        }
    }
    requests.post(fb_url, json=data_quick_replies)

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

    requests.post(fb_url, json=data_misc_buttons)

def reply_auth_delete(sender):
    data_quick_replies = {
        "recipient": {"id": sender},
        "message": {
            "text": "Вы хотите удалить авторизацию?",
            "quick_replies": [
                {
                    "content_type": "text",
                    "title": "Да",
                    "payload": "auth.delete.yes"
                },
                {
                    "content_type": "text",
                    "title": "Нет",
                    "payload": "auth.delete.no"
                }
            ]
        }
    }
    requests.post(fb_url, json=data_quick_replies)
