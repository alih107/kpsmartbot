from flask import Flask, request
import requests

app = Flask(__name__)

def telegram_audio(url, source):

@app.route('/bot_audio', methods=['POST'])
def handle_incoming_messages():
    data = request.json
    print (data)
    url, topic, source = data['url'], data['topic'], data['source']

    return {'message': 'idi nahui'}, 200

if __name__ == '__main__':
    app.run(debug=True)