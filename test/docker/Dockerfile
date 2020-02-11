FROM minio/mc:latest

# configure pip
ADD BIT_Proxy_CA--public.pem /etc/pki/trust/anchors/
ADD pip.conf /etc

# configure proxy
ARG http_proxy
ARG https_proxy
ARG no_proxy
ENV http_proxy $http_proxy
ENV https_proxy $https_proxy
ENV no_proxy $no_proxy

# install pip3 and pytest
RUN apk add py3-pip && \
    pip3 install -U pip && \
    pip3 install pytest pytest-cov

# remove dummy host configs
ADD mc_config.json /root/.mc/config.json

WORKDIR /code

# keep container running
ENTRYPOINT []
CMD tail -f /dev/null