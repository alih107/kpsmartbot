import helper
from wit import Wit
from pydub import AudioSegment

def handle_voice_message(sender, data):
    helper.reply(sender, "Я получил аудио-сообщение!")