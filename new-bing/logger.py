# coding=utf-8

import logging
import os
from logging import handlers

log_file = 'chat.log'

if os.environ.get('REFRESH_WIZ'):
    log_file = 'refresh_wiz.log'


def init_log():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(pathname)s [line:%(lineno)d] %(levelname)s: %(message)s')
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    th = handlers.RotatingFileHandler('/sanic/logs/{}'.format(log_file), maxBytes=100 * 1024 * 1024, backupCount=10)
    th.setFormatter(fmt)
    logger.addHandler(th)
    return logger


logger = init_log()
