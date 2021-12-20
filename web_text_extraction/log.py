import logging


def setup_logging():
    format = '%(asctime)s %(name)s %(threadName)s %(levelname)s: %(message)s'
    logging.basicConfig(level=logging.INFO, format=format)
