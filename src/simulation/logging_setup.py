import logging
import logging.config
import json
import os

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "source": record.name,
        }
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logging(default_path='logging.json', default_level=logging.INFO, env_key='LOG_CFG'):
    path = os.getenv(env_key, default_path)
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

def get_logger(name):
    return logging.getLogger(name)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            # Use the class directly to avoid import path issues
            '()': JsonFormatter,
        },
        'simple': {
            'format': '%(message)s',
        },
    },
    'handlers': {
        'json_file': {
            'class': 'logging.FileHandler',
            'filename': 'simulation.log',
            'formatter': 'json',
            'level': 'INFO',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': 'INFO',
        },
    },
    'loggers': {
        'simulation': {
            'handlers': ['console', 'json_file'],
            'level': 'INFO',
            'propagate': False,
        }
    },
    'root': {
        'handlers': ['console', 'json_file'],
        'level': 'INFO',
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
