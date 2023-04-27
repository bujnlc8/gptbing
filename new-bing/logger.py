# coding=utf-8

import logging
from logging import handlers


def init_log():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(pathname)s [line:%(lineno)d] %(levelname)s: %(message)s')
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    th = handlers.RotatingFileHandler('/sanic/logs/chat.log', maxBytes=10 * 1024 * 1024)
    th.setFormatter(fmt)
    logger.addHandler(th)
    return logger


logger = init_log()
