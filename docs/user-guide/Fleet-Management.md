# Dynamic fleet management

The fleet is stored in:

```text
/etc/nekonet-autoupdate/fleet.json
```

Servers may be added, changed, disabled, or removed without rebuilding the project.

## API endpoints

```text
GET    /api/v1/fleet
GET    /api/v1/fleet/{id}
PUT    /api/v1/fleet/{id}
DELETE /api/v1/fleet/{id}
```

Example payload:

```json
{
  "id": "new-server",
  "name": "new-server.example",
  "ip": "10.10.0.99",
  "role": "worker",
  "enabled": true,
  "is_coordinator": false,
  "metadata": {
    "region": "canada"
  }
}
```

Disabled servers remain in inventory but are excluded from maintenance.
