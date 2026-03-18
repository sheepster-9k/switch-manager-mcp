ARG BUILD_FROM
FROM ${BUILD_FROM:-ghcr.io/hassio-addons/base:16.3.2}

RUN apk add --no-cache python3 py3-pip py3-virtualenv

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
