from pythonjsonlogger import jsonlogger
import logging
import datetime


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name


logger = logging.getLogger("reviews_service")
logHandler = logging.StreamHandler()
formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)