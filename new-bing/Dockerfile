FROM sanicframework/sanic:3.11-latest

WORKDIR /sanic

COPY app.py EdgeGPT.py cookie.json cookie1.json cookie2.json requirements.txt /sanic/

RUN pip install -r requirements.txt

RUN rm requirements.txt

EXPOSE 8000

CMD ["python", "app.py"]
