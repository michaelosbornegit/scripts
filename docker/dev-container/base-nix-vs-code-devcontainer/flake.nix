{
  description = "A very basic flake supporting multiple systems";

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
        buildInputs = [
          pkgs.nodejs_20
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
