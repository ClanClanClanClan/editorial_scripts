{
  description = "Editorial Scripts V3 - Pristine-Plus Architecture";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication defaultPoetryOverrides;

        # Python application
        editorialScriptsV3 = mkPoetryApplication {
          projectDir = ./.;
          python = pkgs.python311;
          
          # Override problematic packages
          overrides = defaultPoetryOverrides.extend (final: prev: {
            # Fix psycopg2-binary build
            psycopg2-binary = prev.psycopg2-binary.overridePythonAttrs (old: {
              buildInputs = (old.buildInputs or [ ]) ++ [ pkgs.postgresql ];
              nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ pkgs.pkg-config ];
            });

            # Fix lxml build
            lxml = prev.lxml.overridePythonAttrs (old: {
              buildInputs = (old.buildInputs or [ ]) ++ [ pkgs.libxml2 pkgs.libxslt ];
              nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ pkgs.pkg-config ];
            });

            # Fix playwright
            playwright = prev.playwright.overridePythonAttrs (old: {
              # Skip browser installation in Nix build
              installPhase = ''
                ${old.installPhase or ""}
                export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
              '';
            });
          });

          # Runtime dependencies
          buildInputs = with pkgs; [
            postgresql_16
            redis
            chromium  # For Playwright
          ];

          # Set environment variables
          postInstall = ''
            # Create wrapper script with proper environment
            makeWrapper $out/bin/editorial $out/bin/editorial-wrapped \
              --set PLAYWRIGHT_BROWSERS_PATH ${pkgs.playwright-driver.browsers} \
              --set PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD 1
          '';
        };

        # Development shell
        devShell = pkgs.mkShell {
          buildInputs = with pkgs; [
            python311
            poetry
            postgresql_16
            redis
            chromium
            
            # Development tools
            pre-commit
            git
            gh
            
            # Security tools
            trivy
            cosign
            syft
            
            # Kubernetes tools for E2E testing
            kubectl
            kind
            
            # AI Act compliance (placeholder - would need actual tool)
            # ai-act-linter
          ];

          shellHook = ''
            export POETRY_VENV_IN_PROJECT=1
            export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
            export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
            
            echo "🚀 Editorial Scripts V3 Development Environment"
            echo "Python: $(python --version)"
            echo "Poetry: $(poetry --version)"
            echo "PostgreSQL: $(postgres --version)"
            echo ""
            echo "To get started:"
            echo "  poetry install"
            echo "  poetry run pytest"
          '';
        };

        # Docker image
        dockerImage = pkgs.dockerTools.buildImage {
          name = "editorial-scripts-v3";
          tag = "latest";
          
          contents = with pkgs; [
            editorialScriptsV3
            postgresql_16
            redis
            chromium
            cacert  # For HTTPS
          ];

          config = {
            Env = [
              "PYTHONPATH=${editorialScriptsV3}/lib/python3.11/site-packages"
              "PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}"
              "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1"
            ];
            
            ExposedPorts = {
              "8000/tcp" = { };  # FastAPI
              "5432/tcp" = { };  # PostgreSQL
              "6379/tcp" = { };  # Redis
            };
            
            Cmd = [ "${editorialScriptsV3}/bin/editorial" "web" "run" ];
            
            Labels = {
              "org.opencontainers.image.title" = "Editorial Scripts V3";
              "org.opencontainers.image.description" = "Pristine-plus editorial manuscript processing system";
              "org.opencontainers.image.version" = "3.0.0-alpha1";
              "org.opencontainers.image.url" = "https://github.com/editorial-scripts/v3";
              "org.opencontainers.image.source" = "https://github.com/editorial-scripts/v3";
              "org.opencontainers.image.licenses" = "proprietary";
              "org.opencontainers.image.vendor" = "Editorial Scripts";
            };
          };
        };

      in
      {
        packages = {
          default = editorialScriptsV3;
          dockerImage = dockerImage;
        };

        apps = {
          default = flake-utils.lib.mkApp {
            drv = editorialScriptsV3;
            exePath = "/bin/editorial";
          };
        };

        devShells.default = devShell;

        # Checks for `nix flake check`
        checks = {
          # Build the application
          build = editorialScriptsV3;
          
          # Build the Docker image  
          docker = dockerImage;
          
          # Run basic tests (requires test setup)
          test = pkgs.stdenv.mkDerivation {
            name = "editorial-scripts-v3-tests";
            src = ./.;
            buildInputs = [ editorialScriptsV3 pkgs.python311Packages.pytest ];
            checkPhase = ''
              # Basic smoke test
              python -c "import src.foundation.types; print('✓ Foundation types import')"
              python -c "import src.domain.entities; print('✓ Domain entities import')"
              
              # Run fast tests only during flake check
              # pytest tests/unit/foundation/ -v --tb=short || echo "Some tests failed but continuing..."
              
              touch $out
            '';
            installPhase = "mkdir -p $out";
          };
        };

        # Formatter for `nix fmt`
        formatter = pkgs.nixpkgs-fmt;
      }
    );
}