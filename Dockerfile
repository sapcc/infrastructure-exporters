FROM python:3.6-alpine

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
ADD . /usr/src/app
RUN pip install pipenv
RUN pipenv install