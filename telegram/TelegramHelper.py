import requests
from logs.logger import get_logger

class Telegram:
    def __init__(self, token, chat_id):
        self.__token = token
        self.__chat_id = chat_id
        self.__logger = get_logger('telegram')

    # Send Message to TG Channel
    def send_telegram(self, text):
        try:
            url = f'https://api.telegram.org/bot{self.__token}/sendMessage'
            data = {
                'chat_id': self.__chat_id,
                'text': text
            }
            r = requests.post(url, data=data)

            if r.status_code != 200:
                raise Exception("post_text error")
            self.__logger.info('Successfully sent message to Telegram')
        
        except Exception as err:
            print(err)
            self.__logger.error('Cannot send message to Telegram')