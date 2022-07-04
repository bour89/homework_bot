import logging
import os
import requests
import telegram
import time
import sys
from dotenv import load_dotenv
from http import HTTPStatus
from settings import ENDPOINT, HOMEWORK_STATUSES, RETRY_TIME
from telegram.error import TelegramError


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


def send_message(bot, message):
    """Проверка отправки сообщения."""
    logging.info('Попытка отправки сообщения')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение успешно отправлено')
    except TelegramError as error:
        raise Exception('Не удалось отправить сообщение -'
                        f' возникла ошибка {error}')


def get_api_answer(current_timestamp):
    """Проверка получения ответа на запрос к эндпоинту."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(url=ENDPOINT,
                                         headers=HEADERS,
                                         params=params)
    except Exception as error:
        raise Exception(f'Ошибка при запросе к API: {error}.')
    if homework_statuses.status_code != HTTPStatus.OK:
        raise Exception('Эндпоинт не доступен')
    else:
        return homework_statuses.json()


def check_response(response):
    """Проверка корректности ответа API."""
    if not isinstance(response, dict):
        raise TypeError('Неверный тип данных в ответе')
    if ('homeworks' or 'current_date') not in response:
        raise KeyError('Получен неверный ключ в ответе')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise KeyError('Получен неверный ключ в ответе')
    return homeworks


def parse_status(homework):
    """Получение и проверка статуса работы."""
    try:
        homework_name = homework.get('homework_name')
        if homework_name is None:
            raise KeyError('Пустой ключ homework_name')
        homework_status = homework.get('status')
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError as error:
        raise KeyError('Не удалось отправить сообщение -'
                       f' возникла ошибка {error}')
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    if (PRACTICUM_TOKEN or TELEGRAM_TOKEN or TELEGRAM_CHAT_ID) is None:
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logging.basicConfig(level=logging.DEBUG,
                        filename='program.log',
                        format='%(asctime)s, %(levelname)s, %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(handler)
    current_timestamp = 15 * 24 * 60 * 60
    if not check_tokens():
        logger.critical('Отстутвие переменной в окружении')
    status_temp = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                status = parse_status(homework)
            if status_temp != status:
                status_temp = status
                send_message(bot, status)
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
