import logging
import os
import threading
import time

try:
    import psycopg2
except ImportError:
    psycopg2 = None

from prometheus_client import Counter, Gauge, REGISTRY

# Флаг для проверки наличия InfluxDB
INFLUXDB_AVAILABLE = False

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS

    # Попытка настройки InfluxDB (будет пропущена, если сервис недоступен)
    try:
        token = "UeVtpMYBGfA3fENfwoTCfnWJtIEOBA6Mqk9r0F6guxiD1hoD6SMwRvGXx8Z7prultF5fdIemLFHE7qySaqz2FQ=="
        org = "mpt"
        url = "http://localhost:8086"
        bucket = "metrics"

        write_client = InfluxDBClient(url=url, token=token, org=org)
        write_api = write_client.write_api(write_options=SYNCHRONOUS)

        INFLUXDB_AVAILABLE = True
        print("InfluxDB client initialized successfully")
    except Exception as e:
        print(f"InfluxDB connection failed: {e}")
        write_client = None
        write_api = None
except ImportError:
    print("InfluxDB client not available. Metrics will not be sent to InfluxDB.")
    Point = None
    write_client = None
    write_api = None


class ResettableCounter:
    def __init__(self, name, documentation):
        self._counter = Counter(name, documentation)
        self._value = 0
        self.name = name

    def inc(self, amount=1):
        self._value += amount
        self._counter.inc(amount)

    def reset(self):
        try:
            if self.name in REGISTRY._names_to_collectors:
                REGISTRY.unregister(self._counter)
        except:
            pass

        self._value = 0
        self._counter = Counter(self.name, self._counter._documentation)


log_counters = {
    'django_log_info_total': Counter('django_log_info_total', 'Total number of info log messages'),
    'django_log_warning_total': ResettableCounter('django_log_warning_total', 'Total number of warning log messages'),
    'django_log_error_total': Counter('django_log_error_total', 'Total number of error log messages'),
}

database_size_gauge = Gauge('database_size_bytes', 'Size of database in bytes')


class WarningMetricResetter(threading.Thread):
    def __init__(self, reset_interval=300):
        super().__init__()
        self.reset_interval = reset_interval
        self.daemon = True
        self.last_warning_time = 0
        self.running = True

    def run(self):
        while self.running:
            current_time = time.time()
            if current_time - self.last_warning_time > self.reset_interval and self.last_warning_time > 0:
                log_counters['django_log_warning_total'].reset()
                print("Warning counter has been reset automatically")
            time.sleep(10)

    def update_last_warning(self):
        self.last_warning_time = time.time()


warning_resetter = WarningMetricResetter()
warning_resetter.start()


class PrometheusLogHandler(logging.Handler):
    def emit(self, record):
        if record.levelno == logging.INFO:
            log_counters['django_log_info_total'].inc()

            # Send to InfluxDB only if available
            if INFLUXDB_AVAILABLE and Point is not None and write_api is not None:
                try:
                    point = Point("django_log_info_total_influxdb") \
                        .tag("level", "INFO") \
                        .tag("app", "django") \
                        .field("info_influxdb", 1)
                    write_api.write(bucket=bucket, record=point)
                except Exception as e:
                    print(f"Failed to write to InfluxDB: {e}")

        elif record.levelno == logging.WARNING:
            log_counters['django_log_warning_total'].inc()
            warning_resetter.update_last_warning()

            # Send to InfluxDB only if available
            if INFLUXDB_AVAILABLE and Point is not None and write_api is not None:
                try:
                    point = Point("django_log_warning_total_influxdb") \
                        .tag("level", "WARNING") \
                        .tag("app", "django") \
                        .field("warning_influxdb", 1)
                    write_api.write(bucket=bucket, record=point)

                    if log_counters['django_log_warning_total']._value >= 5:
                        alert_point = Point("django_log_warning_threshold") \
                            .tag("level", "WARNING") \
                            .tag("app", "django") \
                            .field("value", log_counters['django_log_warning_total']._value) \
                            .field("threshold_exceeded", True)
                        write_api.write(bucket=bucket, record=alert_point)
                except Exception as e:
                    print(f"Failed to write to InfluxDB: {e}")

        elif record.levelno == logging.ERROR:
            log_counters['django_log_error_total'].inc()

            # Send to InfluxDB only if available
            if INFLUXDB_AVAILABLE and Point is not None and write_api is not None:
                try:
                    point = Point("django_log_error_total_influxdb") \
                        .tag("level", "ERROR") \
                        .tag("app", "django") \
                        .field("error_influxdb", 1)
                    write_api.write(bucket=bucket, record=point)
                except Exception as e:
                    print(f"Failed to write to InfluxDB: {e}")

        # Try to get database size if psycopg2 is available
        if psycopg2 is not None:
            try:
                conn = psycopg2.connect(
                    dbname="workplacesafety",
                    user="postgres",
                    password="143952",
                    host="localhost",
                    port="5432"
                )
                cur = conn.cursor()
                cur.execute("SELECT pg_database_size('workplacesafety')")
                size = cur.fetchone()[0]
                database_size_gauge.set(size)

                # Send to InfluxDB only if available
                if INFLUXDB_AVAILABLE and Point is not None and write_api is not None:
                    try:
                        point = Point("database_size_bytes") \
                            .tag("database", "workplacesafety") \
                            .field("db_size", size)
                        write_api.write(bucket=bucket, record=point)
                    except Exception as e:
                        print(f"Failed to write DB size to InfluxDB: {e}")

                cur.close()
                conn.close()
            except Exception as e:
                print(f"Error getting database size: {e}")

    def reset_warning_counter(self):
        log_counters['django_log_warning_total'].reset()

        # Send to InfluxDB only if available
        if INFLUXDB_AVAILABLE and Point is not None and write_api is not None:
            try:
                reset_point = Point("django_log_warning_reset") \
                    .tag("app", "django") \
                    .field("reset", True)
                write_api.write(bucket=bucket, record=reset_point)
            except Exception as e:
                print(f"Failed to write reset to InfluxDB: {e}")

        print("Warning counter has been manually reset")