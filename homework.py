import logging
import os
import sys
import requests
import time


from http import HTTPStatus
from dotenv import load_dotenv

from exceptions import StatusCodeError, HomeworkError
from exceptions import StatusError

import telegram

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.exit
)


def check_tokens():
    """Функция проверки переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    tokens_exist = True
    missing_tokens = []
    for key, value in tokens.items():
        if not value:
            missing_tokens.append(key)
            tokens_exist = False
    for token in missing_tokens:
        logging.critical(f'Отсутствует переменная окружения: {token}')
    return tokens_exist


def send_message(bot, message):
    """Функция отправки сообщения в чат Telegram."""
    logging.debug('Попытка отправки сообщения.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено: {message}')
    except Exception as error:
        logging.error(error)


def get_api_answer(timestamp):
    """Функция запроса к ENDPOINT и получения ответа."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise StatusCodeError(response)
        return response.json()
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к ENDPOINT: {error}')


def check_response(response):
    """Функция проверки типа данных полученного ответа."""
    if not isinstance(response, dict):
        logging.error('Неверный тип данных')
        raise TypeError('Неверный тип данных')
    if not isinstance(response.get('homeworks'), list):
        logging.error('Неверный тип данных ключа домашнего задания')
        raise TypeError('Неверный тип данных ключа домашнего задания')
    return response['homeworks']


def parse_status(homework):
    """Функция обработки статуса работы."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise HomeworkError('Ключ homework_name отсутствует')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise StatusError('Неизвестный статус работы')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Отсутсвуют переменные окружения')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            responce = get_api_answer(timestamp)
            homework = check_response(responce)
            last_message = ''
            if homework:
                message = parse_status(homework[0])
            else:
                message = 'Новых статусов нет.'
            if message != last_message:
                send_message(bot, message)
                last_message = message
            timestamp = responce.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != last_message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
