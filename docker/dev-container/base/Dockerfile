FROM ubuntu:latest

# Update and install necessary packages
RUN apt-get update && \
    apt-get install -y \
    zsh \
    git \
    wget \
    curl \
    sudo \
    gpg \
    python3-venv \
    build-essential \
    screen

# Set the default user for the container
ENV USER mike
RUN useradd -ms /bin/zsh $USER
RUN echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
USER $USER

# Set the ZSH_THEME and add the plugin to .zshrc
COPY .zshrc /home/$USER/.zshrc

COPY .screenrc /home/$USER/.screenrc

COPY permissions_docker.sh /home/$USER/permissions_docker.sh

# Install Oh My Zsh
RUN sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# Set the default shell to zsh
SHELL ["/bin/zsh", "-c"]

# Install NVM
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash

# Switch to root temporarily to install Visual Studio Code CLI
USER root

# Install Visual Studio Code CLI
RUN wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
RUN sudo install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg
RUN sudo sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
RUN rm -f packages.microsoft.gpg

RUN apt-get update && apt-get install -y code

# Install Docker client
RUN curl -fsSL https://get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    rm get-docker.sh

# Switch back to the non-root user
USER $USER

WORKDIR /home/$USER

# install VS Code extensions
RUN code --install-extension ms-python.python --extensions-dir "./.vscode-server/extensions" --user-data-dir "./.vscode-server/settings"
RUN code --install-extension ms-azuretools.vscode-docker --extensions-dir "./.vscode-server/extensions" --user-data-dir "./.vscode-server/settings"
RUN code --install-extension github.copilot --extensions-dir "./.vscode-server/extensions" --user-data-dir "./.vscode-server/settings"
RUN code --install-extension dbaeumer.vscode-eslint --extensions-dir "./.vscode-server/extensions" --user-data-dir "./.vscode-server/settings"
RUN code --install-extension johnpapa.vscode-peacock --extensions-dir "./.vscode-server/extensions" --user-data-dir "./.vscode-server/settings"

RUN mkdir dev

RUN git config --global user.name "Mike Osborne"
RUN git config --global user.email "resonatortune@gmail.com"

# Define default command (you can override it when running the container)
CMD code tunnel --name ${USER}
# CMD code tunnel --extensions-dir "./.vscode-server/extensions" --user-data-dir "./.vscode-server/settings" --name $USER
