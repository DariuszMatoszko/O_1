from __future__ import annotations

import argparse
import json

from runtime_utils import (
    cleanup_sessions,
    create_session,
    ensure_runtime_files,
    load_json,
    portals_path,
    selectors_path,
    session_paths,
    update_run_info,
)


def log_result(log_path: str, payload: dict[str, str]) -> None:
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(payload, ensure_ascii=False))
        log_file.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run F001 portal automation")
    parser.add_argument("number", nargs="?", default="UNKNOWN", help="Portal number")
    parser.add_argument("--portal-key", default="UNKNOWN", help="Portal key")
    args = parser.parse_args()

    ensure_runtime_files()
    cleanup_sessions()
    session_root = create_session(args.portal_key, args.number)
    session_info = session_paths(session_root)

    portals = load_json(portals_path(), {})
    portal_data = portals.get(args.portal_key, {})

    update_run_info(
        session_root,
        {
            "portal_key": args.portal_key,
            "last_number": args.number,
            "run_count": 1,
        },
    )

    from automation.portal_runner import run_portal_flow

    selectors = load_json(selectors_path(), {})

    result = run_portal_flow(args.number, portal_data, selectors, session_info)

    log_result(
        session_info["log_path"],
        {
            "status": result.status,
            "last_step": result.last_step,
            "message": result.message,
            "detail": result.detail,
            "found": str(result.found),
            "screenshot_path": result.screenshot_path or "",
        },
    )
    update_run_info(
        session_root,
        {
            "last_status": result.status,
            "last_step": result.last_step,
        },
    )
    print(
        json.dumps(
            {
                "status": result.status,
                "last_step": result.last_step,
                "message": result.message,
                "detail": result.detail,
                "found": result.found,
                "screenshot_path": result.screenshot_path,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
