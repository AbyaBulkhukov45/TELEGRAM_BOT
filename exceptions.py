class MissingTokensError(Exception):
    """
    Исключение, возникающее при
    отсутствии необходимых
    переменных окружения.
    """
    pass

class StatusCodeError(Exception):
    """
    Исключение, возникающее
    при некорректном статус-коде
    ответа на запрос.
    """
    pass

class HomeworkError(Exception):
    """
    Исключение, возникающее
    при ошибке обработки данных
    о домашнем задании.
    """
    pass

class StatusError(Exception):
    """
    Исключение, возникающее
    при неизвестном статусе работы
    по домашнему заданию.
    """
    pass
