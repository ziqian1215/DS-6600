# syntax=docker/dockerfile:1

FROM python:3.13.7-trixie

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

WORKDIR /DS-6600

EXPOSE 8050

CMD ["python", "app/app.py"]