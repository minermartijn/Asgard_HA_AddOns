FROM python:3.11-alpine

# System deps
RUN apk add --no-cache bash jq curl gcc musl-dev

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app
COPY run.sh /run.sh
RUN chmod a+x /run.sh

ENV PYTHONPATH=/app

CMD [ "/run.sh" ]
