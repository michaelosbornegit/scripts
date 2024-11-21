FROM debian:stable-slim

RUN apt update && apt install -y \
    direnv

COPY post-install-setup.sh /tmp/post-install-setup.sh