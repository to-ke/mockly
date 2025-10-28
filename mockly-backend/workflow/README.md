This directory is a placeholder for workflow definitions used by the backend Docker build.

The original Dockerfile expects `workflow/` to exist and copies it into the image. If you have workflow configuration (e.g., flow definitions, scripts, or YAML files), place them here.

If this directory is intentionally unused, you can either keep this placeholder or remove the `COPY workflow ./workflow` line from `Dockerfile`.

Replace this README with real workflow files as needed.
