"""Development entrypoint: run the FastAPI control plane with uvicorn.

Production uses the systemd unit (`deploy/trinohub.service`), which runs the
same app via `uvicorn trinohub.api:app`. This script mirrors that for local
runs. FastAPI (`trinohub.api`) is the single source of truth for routing.
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the TrinoHub control-plane server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development.")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("trinohub.api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
