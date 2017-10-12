from flask import Flask, request, jsonify
import requests
import xml.etree.ElementTree as ET
from wit import Wit
from pydub import AudioSegment
import os
import logging

app = Flask(__name__)
uuid = "FF83B58DC263F322AC168932DF0DFDBB"
api_key = "1ed1cc83-4c28-44d1-8d40-5942c9875310"
client = Wit('TCLMX5YEBCRG5TO2TLW3VJCOGFOWMOJW')
logging.basicConfig(filename='log_audio.log', level=logging.INFO,
                    format='[%(levelname)s] (%(threadName)-10s) %(message)s')


def yandex_api_post(voice_filename_wav, topic, lang=None):
    headers = {'Content-Type': 'audio/x-wav'}
    url = 'http://asr.yandex.net/asr_xml?uuid=' + uuid + '&key=' + api_key + '&topic=' + topic
    if lang == 'en-US':
        url += '&lang=' + lang
    return requests.post(url, data=open(voice_filename_wav, 'rb'), headers=headers)

def extract_digits(message):
    numbers = '0123456789'
    for i in message:
        if not i in numbers:
            message = message.replace(i, '')
    return message

@app.route('/bot_audio', methods=['POST'])
def handle_incoming_messages():
    data = request.json
    logging.info(data)
    voice_url, topic, source, sender = data['url'], data['topic'], data['source'], data['id']
    g = requests.get(voice_url, stream=True)
    count = 0
    while g.status_code != 200 and count < 10:
        g = requests.get(voice_url, stream=True)
        count += 1
    if g.status_code != 200:
        return 404

    voice_filename = "voice_" + sender + ".mp4"
    voice_filename_wav = "voice_" + sender + ".wav"
    with open(voice_filename, "wb") as o:
        o.write(g.content)
    if source == 'telegram':
        AudioSegment.from_file(voice_filename, "ogg").export(voice_filename_wav, format="wav")
    elif source == 'facebook':
        try:
            AudioSegment.from_file(voice_filename, "mp4").export(voice_filename_wav, format="wav")  # android
        except:
            AudioSegment.from_file(voice_filename, "aac").export(voice_filename_wav, format="wav")  # iphone

    r = yandex_api_post(voice_filename_wav, topic)
    try:
        os.remove(voice_filename)
        os.remove(voice_filename_wav)
    except:
        pass
    root = ET.fromstring(r.text)
    if root.attrib['success'] == '0':
        return 404
    if topic == 'numbers':
        yandex_numbers = extract_digits(root[0].text)
        return jsonify({'numbers': yandex_numbers}), 200
    elif topic == 'queries':
        try:
            resp = client.message(root[0].text)
        except:
            return 404
        if source == 'telegram':
            return jsonify(resp), 200
        elif source == 'facebook':
            entities = resp['entities']
            if 'intent' in entities:
                max_confidence = -1
                intent = ''
                for i in entities['intent']:
                    if i['confidence'] > max_confidence:
                        max_confidence = i['confidence']
                        intent = i['value']
                return jsonify({'intent': intent}), 200
        else:
            return 404

    return jsonify({'message': 'idi nahui'}), 200

if __name__ == '__main__':
    app.run(debug=True)