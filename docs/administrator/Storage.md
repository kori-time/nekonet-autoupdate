# Storage behavior

NekoNet AutoUpdate uses this preference order:

```text
MySQL/MariaDB → PostgreSQL → SQLite → JSON
```

Database connection failures do not stop maintenance when another provider is healthy.

Every checkpoint is written to all currently healthy providers. SQLite and JSON remain available as local mirrors. Failed MySQL or PostgreSQL providers are checked repeatedly in the background. When one reconnects, the newest committed state is written back automatically.

Maintenance stops only when no provider can accept the checkpoint.
