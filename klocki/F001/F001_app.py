from __future__ import annotations

import argparse
import json
import os

from automation.portal_runner import run_portal_flow


LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "F001.log")


def log_result(payload: dict[str, str]) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(payload, ensure_ascii=False))
        log_file.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run F001 portal automation")
    parser.add_argument("number", nargs="?", default="UNKNOWN", help="Portal number")
    args = parser.parse_args()

    result = run_portal_flow(args.number)
    log_result(
        {
            "status": result.status,
            "last_step": result.last_step,
            "message": result.message,
            "detail": result.detail,
            "found": str(result.found),
        }
    )
    print(
        json.dumps(
            {
                "status": result.status,
                "last_step": result.last_step,
                "message": result.message,
                "detail": result.detail,
                "found": result.found,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
