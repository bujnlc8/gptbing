# coding=utf-8

import os
from email.header import Header
from email.mime.text import MIMEText
from smtplib import SMTP_SSL

HOST_SERVER = 'smtp.qq.com'

MAIL_SENDER = os.environ.get('MAIL_SENDER')
MAIL_SENDER_PASSWD = os.environ.get('MAIL_SENDER_PASSWD')
MAIL_RECEIVER = os.environ.get('MAIL_RECEIVER')
MAIL_RECEIVER = MAIL_RECEIVER or MAIL_SENDER


def _send_mail(sender, sender_passwd, receiver, subject, body):
    try:
        smtp = SMTP_SSL(HOST_SERVER, port=465)
        smtp.ehlo(HOST_SERVER)
        smtp.login(sender, sender_passwd)

        msg = MIMEText(body, "plain", 'utf-8')
        msg["Subject"] = Header(subject, 'utf-8')
        msg["From"] = sender
        msg["To"] = receiver
        smtp.sendmail(sender, receiver, msg.as_string())
        smtp.quit()
    except:
        pass


def send_mail(subject, body):
    if '无权限使用此服务' in body:
        return
    subject = '【New Bing】' + subject
    _send_mail(MAIL_SENDER, MAIL_SENDER_PASSWD, MAIL_RECEIVER, subject, body)
