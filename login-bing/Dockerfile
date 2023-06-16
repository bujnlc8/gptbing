FROM python:3.11.4-slim-buster

ENV DEBIAN_FRONTEND noninteractive

WORKDIR /bing

COPY chrome-linux/chromedriver chrome-linux/google-chrome-stable_current_amd64.deb requirements.txt login.py send_mail.py /bing/

RUN apt update && apt install -y cron

RUN pip install -r requirements.txt

RUN dpkg -i google-chrome-stable_current_amd64.deb;exit 0

RUN apt install -f -y

RUN rm -rf google-chrome-stable_current_amd64.deb requirements.txt /var/lib/apt

RUN ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

CMD crontab /etc/cron.d/loginbing && cron && tail -f /bing/cron.log
