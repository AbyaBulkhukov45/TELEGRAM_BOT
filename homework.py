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
from telegram.error import TimedOut

load_dotenv()

PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS: dict = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.exit
)


def check_tokens() -> bool:
    """Функция проверки переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot: telegram.Bot, message: str) -> None:
    """Функция отправки сообщения в чат Telegram."""
    logging.debug('Попытка отправки сообщения.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено: {message}')
    except TimedOut as error:
        logging.error(f'Ошибка отправки сообщения: {error}')
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка Telegram: {error}')
    except Exception as error:
        logging.error(f'Неизвестная ошибка: {error}')


def get_api_answer(timestamp: int) -> dict:
    """Функция запроса к ENDPOINT и получения ответа."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise StatusCodeError(response)
        return response.json()
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к ENDPOINT: {error}')


def check_response(response: dict) -> list:
    """Функция проверки типа данных полученного ответа."""
    if not isinstance(response, dict):
        error_message = 'Неверный тип данных: ожидается dict, получен ' + str(type(response))
        logging.error(error_message)
        raise TypeError(error_message)

    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        error_message = 'Неверный тип данных ключа домашнего задания: ожидается list, получен ' + str(type(homeworks))
        logging.error(error_message)
        raise TypeError(error_message)

    return homeworks



def parse_status(homework: dict) -> str:
    """Функция обработки статуса работы."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise HomeworkError('Ключ homework_name отсутствует')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise StatusError('Неизвестный статус работы')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Отсутсвуют переменные окружения')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'Новых статусов нет.'
            if message != last_message:
                send_message(bot, message)
                last_message = message
            timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != last_message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
