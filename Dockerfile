FROM python:3.6-alpine

RUN apk add dumb-init
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
ADD . /usr/src/app
RUN pip install pipenv
RUN pipenv install

ENTRYPOINT ["./entrypoint.sh"]

