FROM debian:stable-slim

# Update and install required packages
RUN apt update && apt install -y \
    direnv \
    sudo \
    git \
    zsh

# Create vscode user and add to sudo group
RUN useradd -m -s /bin/bash vscode && \
    usermod -aG sudo vscode && \
    echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set up environment for vscode user
COPY post-install-setup.sh /tmp/post-install-setup.sh
RUN chown vscode:vscode /tmp/post-install-setup.sh && \
    chmod +x /tmp/post-install-setup.sh

USER vscode

RUN git config --global --add safe.directory /workspaces/*

# Set the working directory
WORKDIR /workspaces
