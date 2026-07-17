#!/usr/bin/env python3
from __future__ import annotations

import ipaddress
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text()) if path.exists() else {"servers": []}
servers = data.setdefault("servers", [])


def show_servers() -> None:
    print("\nConfigured fleet:")

    for index, server in enumerate(servers, start=1):
        print(
            f"{index:2}) "
            f"{server.get('id', '?'):16} "
            f"{server.get('name', '?'):32} "
            f"{server.get('ip', '?'):15} "
            f"enabled={server.get('enabled', True)}"
        )


def validate(candidate: dict, ignored: dict | None = None) -> None:
    ipaddress.ip_address(candidate["ip"])

    for server in servers:
        if server is ignored:
            continue

        if server.get("id") == candidate["id"]:
            raise ValueError("Duplicate server ID")

        if server.get("name") == candidate["name"]:
            raise ValueError("Duplicate hostname")

        if server.get("ip") == candidate["ip"]:
            raise ValueError("Duplicate IP address")


def prompt_server(existing: dict | None = None) -> dict:
    existing = existing or {}

    def ask(label: str, key: str, default: str = "") -> str:
        current = existing.get(key, default)
        value = input(f"{label} [{current}]: ").strip()
        return value or str(current)

    server = dict(existing)
    server["id"] = ask("Server ID", "id")
    server["name"] = ask("Hostname", "name")
    server["ip"] = ask("Private or public IP", "ip")
    server["role"] = ask("Description or role", "role")

    server["enabled"] = ask(
        "Enabled (yes/no)",
        "enabled",
        "yes",
    ).lower() in {"yes", "y", "true", "1"}

    server["is_coordinator"] = ask(
        "Coordinator (yes/no)",
        "is_coordinator",
        "no",
    ).lower() in {"yes", "y", "true", "1"}

    server.setdefault("metadata", {})
    return server


while True:
    show_servers()

    print(
        "\n"
        "1) Add\n"
        "2) Edit\n"
        "3) Enable or disable\n"
        "4) Remove\n"
        "5) Save and exit\n"
        "6) Exit without saving"
    )

    selection = input("Selection: ").strip()

    try:
        if selection == "1":
            new_server = prompt_server()
            validate(new_server)
            servers.append(new_server)

        elif selection == "2":
            index = int(input("Server number: ")) - 1
            existing = servers[index]
            updated = prompt_server(existing)
            validate(updated, existing)
            servers[index] = updated

        elif selection == "3":
            index = int(input("Server number: ")) - 1
            servers[index]["enabled"] = not servers[index].get(
                "enabled",
                True,
            )

        elif selection == "4":
            index = int(input("Server number: ")) - 1
            servers.pop(index)

        elif selection == "5":
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, indent=2) + "\n")
            temporary.replace(path)
            print(f"Saved {path}")
            break

        elif selection == "6":
            break

    except (ValueError, IndexError) as error:
        print(f"Error: {error}")
