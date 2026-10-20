{
  description = "Medizinische Wissensdatenbank - Medical Knowledge Database";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          name = "medwiss-db";

          packages = with pkgs; [
            # Node.js and npm (bundled together)
            nodejs_22
            bun

            # Docker (for docker-compose)
            docker-compose

            # Development tools
            git
            ruff
            (python312.withPackages (p: with p; [
              fastapi
              sqlalchemy
              pydantic
              pydantic-settings
              email-validator
              pgvector
              uvicorn
              psycopg2
              bcrypt
              python-jose
              passlib
              alembic
              pytest
              requests
              httpx
              pytesseract
              pillow
              pdf2image
              watchdog
              pyyaml
              python-multipart
              rich
            ]))
          ];

          # Python environment setup
          shellHook = ''
            export PYTHONPATH="$PWD:$PYTHONPATH"
            export DATABASE_URL="postgresql://medwiss:changeme@localhost:5432/medwiss"
            
            # Node version check
            echo "Node.js: $(node --version)"
            echo "bun: $(bun --version)"
            echo "Python: $(python --version)"
            
            # Hint for frontend
            echo ""
            echo "Frontend UI: cd ui && bun install && bun run dev"
            echo "Or use: ./start.sh"
          '';

          # Variables for frontend build
          APP_PORT = 5175;
          API_PORT = 8000;
        };
      }
    );
}
