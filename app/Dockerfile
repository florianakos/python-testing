FROM python:3.8-alpine

WORKDIR /app

COPY ./requirements.txt ./

RUN addgroup -S noobs \
    && adduser -D  -u 1000 noobs -G noobs \
    && apk add --no-cache --virtual .pynacl_deps build-base python3-dev libffi-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .pynacl_deps gcc musl-dev \
    && rm requirements.txt

COPY --chown=noobs:noobs submitter.py .

USER noobs

CMD [ "python", "submitter.py" ]
