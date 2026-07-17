from __future__ import annotations
import argparse
import asyncio
import json
from nekonet_autoupdate.config import Settings
from nekonet_autoupdate.service import CoordinatorService
from nekonet_autoupdate.models.fleet import FleetServer

def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run")
    upsert = commands.add_parser("fleet-upsert")
    upsert.add_argument("json_file")
    remove = commands.add_parser("fleet-remove")
    remove.add_argument("server_id")
    args = parser.parse_args()
    service = CoordinatorService(Settings())

    if args.command == "run":
        asyncio.run(service.run())
    elif args.command == "fleet-upsert":
        payload = FleetServer.model_validate_json(open(args.json_file).read())
        print(service.fleet.upsert(payload).model_dump_json(indent=2))
    elif args.command == "fleet-remove":
        print(json.dumps({"removed": service.fleet.remove(args.server_id)}))

if __name__ == "__main__":
    main()
