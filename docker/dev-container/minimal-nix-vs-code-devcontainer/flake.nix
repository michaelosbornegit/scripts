{
  description = "A basic flake supporting linux and mac";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-24.05";
  };

  outputs = { self, nixpkgs, ... }:
    let
      lib = nixpkgs.lib;
      systems = [ "aarch64-linux" "x86_64-linux" ];
      devShellForSystem = system: let
        pkgs = import nixpkgs { 
          inherit system; 
          # config.allowUnfree = true; # Needed for terraform
        };
      in pkgs.mkShell {
        buildInputs = with pkgs; [
          zsh
          nodejs_20
          # htop
          # jdk8
          # python3
          # docker
          azure-cli
          # terraform
          # dotnet-sdk_8
          # neo-cowsay
          gh
        ];
      };
    in
    {
      devShells = lib.listToAttrs (map (system: {
        name = system;
        value = {
          default = devShellForSystem system;
        };
      }) systems);
    };
}
