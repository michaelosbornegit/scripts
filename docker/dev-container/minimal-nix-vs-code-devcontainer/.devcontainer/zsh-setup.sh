# Add Znap for zsh dependencies
echo '[[ -r ~/Repos/znap/znap.zsh ]] || git clone --depth 1 -- https://github.com/marlonrichert/zsh-snap.git ~/Repos/znap' >> /home/vscode/.zshrc && \
    echo 'source ~/Repos/znap/znap.zsh' >> /home/root/.zshrc

# Add zsh plugins
echo 'znap source marlonrichert/zsh-autocomplete' >> /home/root/.zshrc && \
    echo 'znap source zsh-users/zsh-autosuggestions' >> /home/root/.zshrc && \
    echo 'znap source zsh-users/zsh-syntax-highlighting' >> /home/root/.zshrc

# Add direnv to zsh
echo 'eval "$(direnv hook zsh)"' >> /home/root/.zshrc