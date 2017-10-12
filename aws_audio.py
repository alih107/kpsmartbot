from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/kpsmartbot', methods=['POST'])
def handle_incoming_messages():
    data = request.json

    return "ok", 200

if __name__ == '__main__':
    app.run(debug=True)