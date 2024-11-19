# Use the official VS Code Alpine base image
FROM mcr.microsoft.com/vscode/devcontainers/base:alpine
# Maybe someday..
# FROM alpine:latest

# Install dependencies required for Nix
USER root
RUN apk update && apk add --no-cache \
    curl \
    xz \
    ca-certificates \
    direnv

# Create /nix directory and give permissions to vscode user
RUN mkdir -m 0755 /nix && chown vscode:vscode /nix

# Copy Nix configuration
COPY nix.conf /nix/nix.conf
RUN chown vscode:vscode /nix/nix.conf
ENV NIX_CONF_DIR=/nix

# Switch to vscode user
USER vscode

# Install Nix package manager without daemon mode
ENV USER=vscode
RUN curl -L https://nixos.org/nix/install | sh -s -- --no-daemon

# Set environment variables for Nix
ENV NIX_PATH=/home/vscode/.nix-defexpr/channels
ENV PATH=/home/vscode/.nix-profile/bin:/home/vscode/.nix-profile/sbin:$PATH

# # Source Nix in the shell
# RUN echo '. /home/vscode/.nix-profile/etc/profile.d/nix.sh' >> /home/vscode/.bashrc

# add Znap for zsh dependencies
RUN echo '[[ -r ~/Repos/znap/znap.zsh ]] || git clone --depth 1 -- https://github.com/marlonrichert/zsh-snap.git ~/Repos/znap' >> /home/vscode/.zshrc && \
    echo 'source ~/Repos/znap/znap.zsh' >> /home/vscode/.zshrc

# add zsh plugins
RUN echo 'znap source marlonrichert/zsh-autocomplete' >> /home/vscode/.zshrc && \
    echo 'znap source zsh-users/zsh-autosuggestions' >> /home/vscode/.zshrc && \
    echo 'znap source zsh-users/zsh-syntax-highlighting' >> /home/vscode/.zshrc

# add direnv to zsh
RUN echo 'eval "$(direnv hook zsh)" >/dev/null' >> /home/vscode/.zshrc

# Set the working directory
WORKDIR /workspace
