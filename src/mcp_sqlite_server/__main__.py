"""Entry point: python -m mcp_sqlite_server <db_path> [--allow-writes] [--unsafe]"""
import argparse
import sys
from .server import build_server


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mcp-sqlite-server",
        description="MCP server exposing SQLite tools to an MCP client (e.g., Claude Desktop).",
    )
    parser.add_argument("db_path", help="Path to the SQLite database file.")
    parser.add_argument(
        "--allow-writes",
        action="store_true",
        help="Enable execute_write tool (INSERT / UPDATE / DELETE). Off by default.",
    )
    parser.add_argument(
        "--unsafe",
        action="store_true",
        help="Allow DROP/TRUNCATE/ATTACH and other destructive operations. Use with caution.",
    )
    args = parser.parse_args()

    server = build_server(
        db_path=args.db_path,
        allow_writes=args.allow_writes,
        unsafe=args.unsafe,
    )

    try:
        server.run()
    except KeyboardInterrupt:
        print("Shutting down.", file=sys.stderr)


if __name__ == "__main__":
    main()
