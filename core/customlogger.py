# core/customlogger.py - упрощенная версия для Railway
import logging

class SimpleLogHandler(logging.Handler):
    def emit(self, record):
        # Простое логирование без внешних зависимостей
        pass