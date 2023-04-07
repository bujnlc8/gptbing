# coding=utf-8

from email.header import Header
from email.mime.text import MIMEText
from smtplib import SMTP_SSL

HOST_SERVER = 'smtp.qq.com'


def send_mail(sender, sender_passwd, receiver, subject, body):
    smtp = SMTP_SSL(HOST_SERVER, port=465)
    smtp.ehlo(HOST_SERVER)
    smtp.login(sender, sender_passwd)

    msg = MIMEText(body, "plain", 'utf-8')
    msg["Subject"] = Header(subject, 'utf-8')
    msg["From"] = sender
    msg["To"] = receiver
    smtp.sendmail(sender, receiver, msg.as_string())
    smtp.quit()
