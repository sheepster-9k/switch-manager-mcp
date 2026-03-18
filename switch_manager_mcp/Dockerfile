ARG BUILD_FROM
FROM ${BUILD_FROM:-ghcr.io/hassio-addons/base:16.3.2}

RUN apk add --no-cache python3 py3-pip

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
