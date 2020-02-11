FROM minio/mc:latest

# install pip3 and pytest
RUN apk add py3-pip git && \
    pip3 install -U pip && \
    pip3 install pytest pytest-cov codecov

# remove dummy host configs
ADD mc_config.json /root/.mc/config.json

WORKDIR /code

# keep container running
ENTRYPOINT []
CMD tail -f /dev/null