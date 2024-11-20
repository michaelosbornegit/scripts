{
  description = "A basic flake supporting linux and mac";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-23.05";
  };

  outputs = { self, nixpkgs, ... }:
    let
      lib = nixpkgs.lib;
      systems = [ "aarch64-linux" "x86_64-linux" ];
      devShellForSystem = system: let
        pkgs = import nixpkgs { inherit system; };
      in pkgs.mkShell {
        buildInputs = with pkgs; [
          # htop
          # nodejs_20
          # python3
          # docker
          # azure-cli
          # terraform
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
