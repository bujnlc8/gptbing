FROM sanicframework/sanic:3.11-latest

WORKDIR /sanic

COPY keywords.txt dfa.py send_mail.py logger.py app.py EdgeGPT.py BingImageCreator.py conversation_ctr.py requirements.txt /sanic/

RUN pip install -r requirements.txt

RUN rm requirements.txt

EXPOSE 8000

CMD ["python", "app.py"]
