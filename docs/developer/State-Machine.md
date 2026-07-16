# State Machine

`idle → leader-election → network-preflight → storage-selection → regular-updates → regular-reboots → server-b → server-a → complete`

Any active phase may transition to `failed`. `failed` and `complete` are terminal.
