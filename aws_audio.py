from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/bot_audio', methods=['POST'])
def handle_incoming_messages():
    data = request.json
    print (data)
    return "ok", 200

if __name__ == '__main__':
    app.run(debug=True)