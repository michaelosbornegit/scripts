# Use the official VS Code Alpine base image
# FROM mcr.microsoft.com/vscode/devcontainers/base:alpine
# Maybe someday..
FROM debian:stable-slim

RUN apt update && apt install -y \
    direnv

COPY post-install-setup.sh /tmp/post-install-setup.sh

# Install dependencies required for Nix
# USER root
# RUN apk update && apk add --no-cache \
#     direnv

# # Create /nix directory and give permissions to vscode user
# RUN mkdir -m 0755 /nix && chown vscode:vscode /nix

# # Copy Nix configuration
# COPY nix.conf /nix/nix.conf
# RUN chown vscode:vscode /nix/nix.conf
# ENV NIX_CONF_DIR=/nix

# # Switch to vscode user
# USER vscode

# # Install Nix package manager without daemon mode
# ENV USER=vscode
# RUN sh <(curl -L https://nixos.org/nix/install) --no-daemon

# # Set environment variables for Nix
# ENV NIX_PATH=/home/vscode/.nix-defexpr/channels
# ENV PATH=/home/vscode/.nix-profile/bin:/home/vscode/.nix-profile/sbin:$PATH

# # Set the working directory
# WORKDIR /workspace
