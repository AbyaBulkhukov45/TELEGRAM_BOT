import logging
import os
import sys
import time
import requests
import telegram

from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PR_TOKEN')
TELEGRAM_TOKEN = os.getenv('TEL_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TEL_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
formatter = '%(asctime)s, %(levelname)s, %(message)s'
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения через Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Сообщение отправлено через Telegram: {message}')
    except telegram.error.TelegramError as e:
        logger.error(f'Ошибка работы с Telegram: {e}')


def get_api_answer(current_timestamp):
    """
    Делает запрос к API Практикум.Домашка.
    Возвращает расшифрованный ответ в формате JSON.
    Изменяет размер времени в формате int в качестве параметра.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        message = 'Не удается связаться с конечной точкой.'
        raise RuntimeError(message) from e
    return response.json()


def check_response(response):
    """
    Проверяет, содержит ли ответ ключ "homeworks".
    Возвращает его значение, если это список.
    """
    if 'homeworks' not in response:
        message = 'В ответе API отсутствует ключ "homeworks".'
        raise ValueError(message)

    hw_list = response['homeworks']

    if not isinstance(hw_list, list):
        message = ('Тип значения "homeworks" в ответе API '
                   f'"{type(hw_list)}" не является списком.'
                   )
        raise TypeError(message)

    return hw_list


def parse_status(homework):
    """
    Получает словарь для домашнего задания.
    Возвращает строку с именем и текущим статусом работы.
    """
    if 'homework_name' not in homework:
        message = 'API вернул домашнее задание без ключа "homework_name".'
        raise KeyError(message)

    homework_name = homework['homework_name']
    homework_status = homework.get('status')

    try:
        verdict = HOMEWORK_VERDICTS[homework_status]
    except KeyError:
        message = f'неизв. cnfn "{homework_status}" для "{homework_name}".'
        raise ValueError(message)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """
    Возвращает False, если одна из переменных TOKENS или CHAT_ID пуста.
    Возвращает True если токены не пусты.
    """
    return all(
        [
            PRACTICUM_TOKEN,
            TELEGRAM_TOKEN,
            TELEGRAM_CHAT_ID,
        ]
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    prev_upd_time = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            hw_list = check_response(response)

            for homework in hw_list:
                upd_time = homework.get('date_updated')

                if upd_time != prev_upd_time:
                    prev_upd_time = upd_time
                    message = parse_status(homework)
                    send_message(bot, message)
            current_timestamp = response['current_date']

        except Exception as e:
            logger.exception(e)
            message = f'Программа столкнулась с ошибкой: {e}'
            logger.error(message)
            send_message(bot, message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
