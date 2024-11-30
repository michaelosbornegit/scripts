# Own workspaces
chown -R vscode /workspaces

# Use official oh-my-zsh installer
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# Add Znap for zsh dependencies
echo '[[ -r ~/Repos/znap/znap.zsh ]] || git clone --depth 1 -- https://github.com/marlonrichert/zsh-snap.git ~/Repos/znap' >> ~/.zshrc && \
    echo 'source ~/Repos/znap/znap.zsh' >> ~/.zshrc

# Add zsh plugins
echo 'znap source marlonrichert/zsh-autocomplete' >> ~/.zshrc && \
    echo 'znap source zsh-users/zsh-autosuggestions' >> ~/.zshrc && \
    echo 'znap source zsh-users/zsh-syntax-highlighting' >> ~/.zshrc

# Add direnv to zsh
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc