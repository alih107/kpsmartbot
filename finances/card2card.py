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
card2card_info = """Информация:\nПереводы возможны только между картами одной МПС: Visa to Visa или 
MasterCard to MasterCard.\nПереводы между Visa и MasterCard возможны, только если одна из карт 
эмитирована банком АО \"Казкоммерцбанк\"."""


def reply_card2card_enter_cardDst(sender, last_sender_message):
    if main.check_login(sender, last_sender_message):
        try:
            cardDsts = last_sender_message['cardDsts']
            assert len(cardDsts) > 0
            buttons = []
            for card in cardDsts:
                card = helper.insert_4_spaces(card)
                buttons.append({"content_type": "text", "payload": "card2card.last", "title": card})
            buttons.append({"content_type": "text", "payload": "card2card.delete", "title": "Удалить карту"})
            buttons.append({"content_type": "text", "payload": "card2card.info", "title": "Информация"})
            data_quick_replies = {
                "recipient": {"id": sender},
                "message": {
                    "text": "Выберите номер карты получателя или введите его\n" + hint_main_menu,
                    "quick_replies": buttons
                }
            }
            requests.post(fb_url, json=data_quick_replies)
        except:
            main.reply(sender, card2card_info +
                       "\n\nВведите 16ти-значный номер карты, на который Вы хотите перевести деньги\n" + hint_main_menu)
        last_sender_message['lastCommand'] = 'card2card'
        main.mongo_update_record(last_sender_message)


def reply_card2card_check_cardDst(sender, message, last_sender_message):
    message = message.replace(' ', '')
    if len(message) != 16:
        main.reply(sender, "Вы ввели не все 16 цифр карты, попробуйте ещё раз")
        return "cardDst.again"
    if not message.isdigit():
        main.reply(sender, "Некоторые введенные Вами цифры не являются цифрами, попробуйте ещё раз")
        return "cardDst.again"
    main.reply(sender, "Введите сумму перевода (от 500 до 494070; комиссия 1,2%, минимум 300 тенге)\n" + hint_main_menu)

    last_sender_message['lastCardDst'] = message
    last_sender_message['payload'] = 'card2card.amount'
    try:
        if not "cardDsts" in last_sender_message:
            last_sender_message['cardDsts'] = []
        if not message in last_sender_message['cardDsts'] and len(last_sender_message['cardDsts']) < 9:
            last_sender_message['cardDsts'].append(message)
    except:
        logging.error(helper.PrintException())
    main.mongo_update_record(last_sender_message)

def reply_card2card_delete(sender, last_sender_message):
    cardDsts = last_sender_message['cardDsts']
    buttons = []
    for card in cardDsts:
        card = helper.insert_4_spaces(card)
        buttons.append({"content_type": "text", "payload": "card2card.delete.card", "title": card})

    data_quick_replies = {
        "recipient": {"id": sender},
        "message": {
            "text": "Выберите карту, чтобы её удалить",
            "quick_replies": buttons
        }
    }
    requests.post(fb_url, json=data_quick_replies)

def reply_card2card_delete_card(sender, text, last_sender_message):
    last_sender_message['cardDsts'].remove(text.replace(' ', ''))
    main.reply(sender, "Карта " + text + " успешно удалёна")
    reply_card2card_enter_cardDst(sender, last_sender_message)

def reply_card2card_amount(sender, message, last_sender_message):
    amount = 0
    minAmount = 500
    maxAmount = 494070
    try:
        amount = int(message)
    except:
        main.reply(sender, "Вы неправильно ввели сумму перевода. Введите сумму заново")
        return "again"

    if amount < minAmount:
        main.reply(sender, "Сумма перевода должна быть не менее " + str(minAmount) + " тг. Введите сумму заново")
        return "again"

    if amount > maxAmount:
        main.reply(sender, "Сумма перевода должна быть не более " + str(maxAmount) + " тг. Введите сумму заново")
        return "again"

    last_sender_message['payload'] = 'card2card.chooseCard'
    last_sender_message['amount'] = amount
    main.mongo_update_record(last_sender_message)
    main.reply_display_cards(sender, last_sender_message)

def reply_card2card_csc(sender, payload, last_sender_message):
    amount = last_sender_message['amount']
    commission = amount * 1.2 / 100;
    if commission < 300:
        commission = 300
    lastCardDst = helper.insert_4_spaces(last_sender_message['lastCardDst'])
    total = amount + commission
    last_sender_message['commission'] = commission
    last_sender_message['total'] = commission
    chosenCard = last_sender_message[payload]

    message = "Вы ввели:\n"
    message += "Номер карты пополнения: " + lastCardDst + '\n'
    message += "Сумма: " + str(amount) + " тг\n"
    message += "Комиссия: " + str(commission) + " тг\n"
    message += "Итого: " + str(total) + " тг\n"
    message += "Карта: " + chosenCard + '\n\n'
    message += "Если всё верно, введите трехзначный код CSC/CVV2 на обратной стороне карты"

    main.reply(sender, message)

def reply_card2card_startPayment(sender, message, last_sender_message):
    if not helper.check_csc(message):
        main.reply(sender, "Вы неправильно ввели трёхзначный код CSC/CVV2 на обратной стороне карты, введите заново")
        return "ok"
    main.reply(sender, "Идет обработка перевода...")
    main.reply_typing_on(sender)
    # 1 - авторизация на post.kz
    try:
        session = main.get_authorized_session(last_sender_message['encodedLoginPass'])
        mobileNumber = last_sender_message['mobileNumber']

        # 2 - вызов getCards()
        url_login6 = 'https://post.kz/mail-app/api/intervale/card?device=mobile'
        sd2 = {"blockedAmount": "", "phone": mobileNumber, "paymentId": "", "returnUrl": "", "transferId": ""}
        r = session.post(url_login6, json=sd2)
        card = r.json()[last_sender_message['chosenCardIndex']]

        # 3 - вызов getToken()
        url_login4 = url + portal_id + '/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'X-Channel-Id': x_channel_id,
                   'X-IV-Authorization': 'Identifier ' + mobileNumber}
        r = session.post(url_login4, headers=headers)
        token = r.json()['token']

        # 4 - вызов startPayment()
        amount = last_sender_message['amount']
        data = {'paymentId': 'MoneyTransfer_KazPost_Card2Card',
                'currency': 'KZT',
                'amount': str(amount) + '00',
                'commission': str(last_sender_message['commission']) + '00',
                'total': str(last_sender_message['total']) + '00',
                'src.type': 'card_id',
                'src.cardId': card['id'],
                'src.csc': message,
                'dst.type': 'card',
                'dst.pan': last_sender_message['lastCardDst'],
                'returnUrl': 'https://transfer.post.kz/?token=' + token}

        url_login5 = url + portal_id + '/payment/' + token + '/start'
        r = session.post(url_login5, data=data, headers=headers)

        # 5 - вызов statusPayment()

        url_login10 = url + portal_id + '/payment/' + token
        r = session.post(url_login10, headers=headers)
        data = r.json()
        state = data['state']
        if state == 'redirect':
            main.reply_send_redirect_url(sender, data['url'])

        card_w_spaces = helper.insert_4_spaces(last_sender_message['lastCardDst'])
        timer = 0
        while timer < timeout:
            time.sleep(1)
            r = session.post(url_login10, headers=headers)
            data = r.json()
            try:
                result_status = data['result']['status']
                if result_status == 'fail':
                    main.reply(sender, "Платеж не был завершен успешно. Попробуйте снова")
                elif result_status == 'success':
                    res = "Поздравляю! Платеж был проведен успешно, карта " + card_w_spaces + " пополнена на сумму " + str(
                        amount) + " тг.\n"
                    res += "Номер квитанции: " + str(data['result']['trxId'])
                    res += ", она доступна в профиле post.kz в разделе История платежей"
                    main.reply(sender, res)
                main.reply_main_menu_buttons(sender, last_sender_message)
                return "ok"
            except:
                pass
            timer += 1

        last_sender_message = main.mongo_get_by_sender(sender)
        if last_sender_message['payload'] == 'card2card.startPayment':
            strminutes = str(timeout // 60)
            main.reply(sender, "Прошло больше " + strminutes + " минут: платеж отменяется")
            main.reply_main_menu_buttons(sender, last_sender_message)
        return "time exceed"
    except:
        main.reply(sender, "Произошла непредвиденная ошибка, попробуйте позднее")
        main.reply_main_menu_buttons(sender, last_sender_message)
        logging.error(helper.PrintException())
        return "fail"