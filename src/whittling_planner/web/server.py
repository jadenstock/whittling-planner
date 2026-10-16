"""Launch the local web app: `uv run whittling-planner-web`."""

import argparse
import threading
import webbrowser

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8003)
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open a browser tab.")
    args = parser.parse_args()

    if not args.no_browser:
        url = f"http://{args.host}:{args.port}"
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    uvicorn.run("whittling_planner.web.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
