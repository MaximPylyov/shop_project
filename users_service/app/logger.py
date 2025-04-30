from pythonjsonlogger import jsonlogger
import logging
import datetime
import socket


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name


class LogstashTcpHandler(logging.Handler):
    def __init__(self, host: str, port: int):
        super().__init__()
        self.host = host
        self.port = port

    def emit(self, record):
        try:
            log_entry = self.format(record)
            with socket.create_connection((self.host, self.port), timeout=1) as sock:
                sock.sendall((log_entry + '\n').encode('utf-8'))
        except Exception:
            self.handleError(record)


def get_logger(name: str = "users_service") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    #для Logstash
    tcp_handler = LogstashTcpHandler("logstash", 5000)
    tcp_handler.setFormatter(CustomJsonFormatter('%(timestamp)s %(level)s %(logger)s %(message)s'))
    logger.addHandler(tcp_handler)
    # для stdout
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(CustomJsonFormatter('%(timestamp)s %(level)s %(logger)s %(message)s'))
    logger.addHandler(stream_handler)
    return logger


logger = get_logger()