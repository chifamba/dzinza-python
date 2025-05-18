# To learn more about how to use Nix to configure your environment
# see: https://firebase.google.com/docs/studio/customize-workspace
{ pkgs, ...}: {
  # Which nixpkgs channel to use.
  channel = "stable-24.11"; # or "unstable"
  # Use https://search.nixos.org/packages to find packages
  packages = [
    pkgs.python3Packages.psycopg2-binary
    pkgs.docker
    pkgs.docker-compose  # Added Docker Compose
    pkgs.python3Packages.transformers
    pkgs.python3Packages.numpy
    pkgs.python3Packages.requests
    pkgs.python3Packages.sentencepiece
    pkgs.python3Packages.torch
    pkgs.python3Packages.datasets
    pkgs.python3Packages.accelerate
    pkgs.python3Packages.pytest
    pkgs.tree-sitter
    pkgs.black
    pkgs.vim
  ]; 
  
  services = {
    docker = {
      enable = true;
    };
  };

  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [ 
      "ms-python.python" 
      "ms-azuretools.vscode-docker"  # Added Docker/Docker Compose extension
    ]; 
    workspace = {
      # Runs when a workspace is first created with this `dev.nix` file
      onCreate = {
        install = "";
        # Open editors for the following files by default, if they exist:
        default.openFiles = [ "README.md" "todo.md" ];
      }; # To run something each time the workspace is (re)started, use the `onStart` hook
    };

    # Enable previews and customize configuration
    previews = {
      enable = false;
      previews = {
        web = {
          command = [ "./devserver.sh" ];
          env = { PORT = "$PORT"; };
          manager = "web";
        };
      };
    };
  };
}