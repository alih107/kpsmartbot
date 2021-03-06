import sys
import linecache
import math

postamat = """Почтомат или постамат – это автоматизированный терминал по выдаче товаров,
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

fastmail_options = """У нас есть несколько опций по ускоренной доставке: «Оптимум аэропорт/почтамт» для срочных 
отправлений до 2-ух кг между Астаной и Алматы , «Планета экспресс РФ» для ускоренных посылок, направленных в РФ, 
Доставкa «День в день» - доставка в день приема между Астаной и Алматы, Доставкa к определенному времени – доставка 
к 11/13 часам на следующий день после отправки, «Доставка по городу», «Моя страна», «Вокзал-Вокзал», Планета экспресс 
СНГ, ДЗ. О каком из этих сервисов Вы бы хотели узнать больше?
"""

postamat_how = """Выберите удобный по расположению и режиму работы почтомат и запишите его индекс. Если Вы отправляете 
посылку из отделения, укажите индекс почтомата, и мобильный телефон получателя. Если Вы оформляете заказ в 
интернет-магазине, в поле Адрес укажите месторасположение почтомата (Например: ТРЦ Мега-Астана - почтомат- 900511) и 
номер своего мобильного телефона (несмотря на наличие отдельного поля для номера мобильного телефона, некоторые 
магазины не указывают его в адресном ярлыке), в поле Индекс (Zip code) – индекс почтомата. До получения посылки, 
следите за тем, чтобы указанный при отправке мобильный телефон подключен, находился в зоне доступа и на нем 
положительный баланс и ожидайте уведомления. После доставки посылки в почтомат Вам поступит SMS-сообщение с 
индивидуальным кодом для открытия ячейки. Хотите ли Вы узнать индекс ближайшего к Вам почтомата?
"""

hybridpost_time = """Доставка гибридной почты осуществляется в течение 1-2 рабочих дней с момента отправки.
"""

postamat_info_access = """Каждая посылка обрабатывается постаматом индивидуально, для открытия ячейки необходимо 
введение индивидуального штрих-кода, привязанного к имени получателя и его номеру телефона.
"""

hybridpost_info = """В настоящий момент мы предлагаем только черно-белую печать для гибридных отправлений.
"""

trackbynumber = """Возможно, номер, по которому Вы пытаетесь отследить данное отправление, не привязан к Вашему 
профилю на Post.kz. Воспользуйтесь номером, привязанным к аккаунту, либо присоедините новый номер.
"""

redirect = """Убедитесь, что статус Вашего отправления «Прибыло и ожидает»; В отправлении указан номер мобильного 
телефона получателя; И указанные индексы места отправки/доставки корректны.
"""

redirect_why = """Убедитесь, что статус Вашего отправления «Прибыло и ожидает»; В отправлении указан номер мобильного 
телефона получателя; И указанные индексы места отправки/доставки корректны.
"""

package_how_long = """Что произойдет, если не получить посылку из постамата в течение трех дней?
"""

trackbynumber_query = """Трекинговый номер - уникальный идентификатор, присваиваемый каждому почтовому отправлению, 
по которому Вы можете отследить свое отправление. Трек-номер присваивается во время отправки почты или, в случае 
получения почты из-за рубежа, при пересечении границы в Казахстане.
"""

main_menu_attachment = {
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
                                    "title": "🔍 Отслеживание",
                                    "payload": "tracking"
                                },
                                {
                                    "type": "postback",
                                    "title": "📍Ближайшие отделения",
                                    "payload": "nearest"
                                },
                                {
                                    "type": "postback",
                                    "title": "💰 Финансы",
                                    "payload": "menu.finances"
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
                                }
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

finances_buttons_attachment = {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": "Финансы",
                            "buttons": [
                                {
                                    "type": "postback",
                                    "title": "📲 Пополнение баланса",
                                    "payload": "balance"
                                },
                                {
                                    "type": "postback",
                                    "title": "🚌 Пополнение Онай",
                                    "payload": "onai"
                                },
                                {
                                    "type": "postback",
                                    "title": "💳 Перевод на карту",
                                    "payload": "card2card"
                                }

                            ]
                        },
                        {
                            "title": "Финансы",
                            "buttons": [
                                {
                                    "type": "postback",
                                    "title": "💸 Перевод на руки",
                                    "payload": "card2cash"
                                },
                                {
                                    "type": "postback",
                                    "title": "📃 Оплата ком.услуг",
                                    "payload": "komuslugi"
                                },
                                {
                                    "type": "postback",
                                    "title": "Главное меню",
                                    "payload": "mainMenu"
                                }
                            ]
                        },
                    ]
                }
            }
        }

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

def insert_spaces_onai(onai):
    res = ''
    index = 0
    for c in onai:
        res += c
        index += 1
        if index in [4, 6, 11, 15]:
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

def extract_digits(message):
    numbers = '0123456789'
    for i in message:
        if not i in numbers:
            message = message.replace(i, '')
    return message

def extract_digits_and_letters(message):
    numbers_digits = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    for i in message:
        if not i in numbers_digits:
            message = message.replace(i, '')
    return message