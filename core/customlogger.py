import logging


class DummyGauge:
    def set(self, value):
        pass


database_size_gauge = DummyGauge()


class SimpleLogHandler(logging.Handler):
    """Простой обработчик логов без внешних зависимостей"""

    def emit(self, record):
        # Простое логирование без prometheus и influxdb
        pass