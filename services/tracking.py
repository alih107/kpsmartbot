import requests
import main

fb_url = main.fb_url
hint_main_menu = main.hint_main_menu

def reply_tracking_enter_number(sender, last_sender_message):
    if not 'trackingNumbers' in last_sender_message:
        last_sender_message['trackingNumbers'] = []
    try:
        trackingNumbers = last_sender_message['trackingNumbers']
        assert len(trackingNumbers) > 0
        text = "Выберите трек-номер или введите его\n" + hint_main_menu
        reply_tracking_quick_replies_with_delete(sender, trackingNumbers, text)
    except:
        main.reply(sender, "Введите трек-номер посылки\n" + hint_main_menu)
    last_sender_message['payload'] = 'tracking'
    main.mongo_update_record(last_sender_message)

def reply_tracking_quick_replies_with_delete(sender, trackingNumbers, text):
    buttons = []
    for num in trackingNumbers:
        buttons.append({"content_type": "text", "payload": "tracking.last", "title": num})
    buttons.append({"content_type": "text", "payload": "tracking.delete", "title": "Удалить трек-номер"})
    data_quick_replies = {
        "recipient": {"id": sender},
        "message": {
            "text": text,
            "quick_replies": buttons
        }
    }
    requests.post(fb_url, json=data_quick_replies)

def reply_tracking(sender, tracking_number, last_sender_message):
    data = requests.get("https://post.kz/external-api/tracking/api/v2/" + tracking_number + "/events").json()
    data2 = requests.get("https://post.kz/external-api/tracking/api/v2/" + tracking_number).json()
    try:
        error = data2['error']
        main.reply(sender, error + '\n(Чтобы узнать статус другой посылки, отправьте её трек-номер либо нажмите (y) для перехода в главное меню)')
        return "not found"
    except:
        new_mapping = requests.get("https://post.kz/static/new_mappings.json").json()
        t_date = data['events'][0]['date']
        t_time = data['events'][0]['activity'][0]['time']
        t_datetime = t_date + " " + t_time
        t_status = data['events'][0]['activity'][0]['status'][0]
        t_address = data2['last']['address']
        t_status_mapping = new_mapping[t_status]['mapping']
        result = "Информация об отправлении " + tracking_number + '\n'
        result += "Статус: " + t_status_mapping + '\n' + t_address + '\n' + t_datetime + '\n'
        result += "(Чтобы узнать статус другой посылки, выберите или отправьте её трек-номер " \
                  "либо нажмите (y) для перехода в главное меню)" + '\n'

        if not tracking_number in last_sender_message['trackingNumbers'] and \
                        len(last_sender_message['trackingNumbers']) < 10:
            last_sender_message['trackingNumbers'].append(tracking_number)

        reply_tracking_quick_replies_with_delete(sender, last_sender_message['trackingNumbers'], result)
        main.mongo_update_record(last_sender_message)
        return "ok"

def reply_tracking_delete(sender, last_sender_message):
    trackingNumbers = last_sender_message['trackingNumbers']
    buttons = []
    for num in trackingNumbers:
        buttons.append({"content_type": "text", "payload": "tracking.delete.number", "title": num})

    data_quick_replies = {
        "recipient": {
            "id": sender
        },
        "message": {
            "text": "Выберите трек-номер, чтобы его удалить",
            "quick_replies": buttons
        }
    }
    requests.post(fb_url, json=data_quick_replies)

def reply_tracking_delete_number(sender, text, last_sender_message):
    last_sender_message['trackingNumbers'].remove(text)
    main.reply(sender, "Трек-номер " + text + " успешно удалён")
    reply_tracking_enter_number(sender, last_sender_message)