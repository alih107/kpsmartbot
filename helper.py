import sys
import linecache
import math
import requests
import constants

ACCESS_TOKEN = constants.ACCESS_TOKEN

what_is_postamat = """Почтомат или постамат – это автоматизированный терминал по выдаче товаров,
заказанных в интернет-магазинах и каталогах, созданный как услуга альтернативной доставки.
Удобство заключается с расположении, гибком режиме работы и отсутствии потери времени в очереди отделения.
"""

hybridpost_def = """Гибридная почта – это новый сервис по доставке электронных писем адресату в виде письма.
Вам больше не нужно печатать письма и упаковывать их в конверты самостоятельно.
Мы сделаем это все за Вас. Все, что от Вас требуется – написать письмо в электронной форме или прикрепить файл 
в формате PDF, указать адрес доставки, а мы распечатаем его, запакуем в конверт и отправим.
"""

what_is_supermarket = """Супермаркет посылок – это почтовое отделение нового формата, работающее по принципу 
самообслуживания, где можно самостоятельно получить посылку, а также отправить ее, не затрачивая много времени.
"""

def reply_typing_on(sender):
    data = {
        "recipient": {"id": sender},
        "sender_action": "typing_on"
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data)

def reply_typing_off(sender):
    data = {
        "recipient": {"id": sender},
        "sender_action": "typing_off"
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data)

def reply(user_id, msg):
    data = {
        "recipient": {"id": user_id},
        "message": {"text": msg}
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data)

def get_distance_in_meters(lat1, lat2, lon1, lon2):
    """
    Расстояние между 2 точками Земли в метрах.
    """
    radius = 6371000
    fi1 = math.radians(lat1)
    fi2 = math.radians(lat2)
    delta_fi = math.radians(lat1 - lat2)
    delta_si = math.radians(lon1 - lon2)
    a = math.sin(delta_fi / 2) ** 2 + math.cos(fi1) * math.cos(fi2) * (math.sin(delta_si / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c
    return round(d)

def insert_4_spaces(card):
    res = ''
    index = 0
    for c in card:
        res += c
        index += 1
        if index in [4, 8, 12]:
            res += ' '

    return res

def insert_space_onai(onai):
    res = ''
    index = 0
    for c in onai:
        res += c
        index += 1
        if index == 15:
            res += ' '
    return res

def isAllDigits(card):
    for c in card:
        try:
            a = int(c)
        except:
            return False

    return True

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    return 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)

def check_csc(csc):
    try:
        number = int(csc)
        if number < 0 or number > 999:
            return False
    except:
        return False
    return True