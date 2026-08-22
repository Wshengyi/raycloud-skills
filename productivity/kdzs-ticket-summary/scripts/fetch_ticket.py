#!/usr/bin/env python3
"""Read one 快递助手 internal ticket without changing server state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import browser_cookie3
import requests

BASE_URL = "https://ticket.kuaidizs.cn"
COOKIE_NAME = "Ticket-Token"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a ticket and its records read-only.")
    parser.add_argument("ticket_id", help="Numeric ticket ID")
    parser.add_argument("--output", type=Path, help="Write JSON to this path")
    return parser.parse_args()


def get_login_context() -> tuple[requests.Session, dict[str, str]]:
    cookies = browser_cookie3.chrome(domain_name="ticket.kuaidizs.cn")
    token = next((cookie.value for cookie in cookies if cookie.name == COOKIE_NAME), "")
    if not token:
        raise RuntimeError("Chrome does not have a valid Ticket-Token cookie; log in first.")

    session = requests.Session()
    session.cookies.update(cookies)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Requested-With": "true",
    }
    return session, headers


def get_json(
    session: requests.Session, headers: dict[str, str], endpoint: str
) -> dict[str, Any]:
    response = session.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 200:
        raise RuntimeError(f"Ticket API error: {data.get('msg', 'unknown error')}")
    return data


def post_json(
    session: requests.Session,
    headers: dict[str, str],
    endpoint: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = session.post(
        f"{BASE_URL}{endpoint}", headers=headers, json=payload, timeout=30
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 200:
        raise RuntimeError(f"Ticket API error: {data.get('msg', 'unknown error')}")
    return data


def decode_account(
    session: requests.Session, headers: dict[str, str], account_encode: str
) -> str:
    decoded = post_json(
        session, headers, "/ticket/decodeAccount", {"accountEncode": account_encode}
    )
    account = decoded.get("data", {}).get("accountDecode")
    if not account:
        raise RuntimeError("Ticket API returned no decoded merchant phone")
    return str(account)


def fetch_ticket(ticket_id: str) -> dict[str, Any]:
    if not ticket_id.isdigit():
        raise ValueError("ticket_id must contain digits only")

    session, headers = get_login_context()
    ticket = get_json(session, headers, f"/ticket/list?id={ticket_id}")
    records = get_json(session, headers, f"/ticket/record/list?ticketId={ticket_id}")

    if ticket.get("total") != 1 or len(ticket.get("rows", [])) != 1:
        raise RuntimeError(f"Expected one ticket, received {ticket.get('total', 0)}")
    if len(records.get("rows", [])) != records.get("total", 0):
        raise RuntimeError("Ticket records are incomplete")

    ticket_row = ticket["rows"][0]
    account_encode = ticket_row.get("accountEncode")
    merchant_phone = (
        decode_account(session, headers, str(account_encode))
        if account_encode
        else "未提供"
    )
    return {"ticket": ticket, "records": records, "merchantPhone": merchant_phone}


def main() -> None:
    args = parse_args()
    result = fetch_ticket(args.ticket_id)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"Saved ticket {args.ticket_id} to {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
