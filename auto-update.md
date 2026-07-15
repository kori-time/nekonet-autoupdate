# NekoNet AutoUpdate

Highly controlled weekly update orchestration for an 18-server Ubuntu 24.04 WireGuard mesh.

## Core safety behavior

The system is fail-closed.

### Update failure

If any regular server fails to update or fails to report a valid result:

- all remaining updates stop immediately;
- the reboot phase does not start;
- Server B does not update;
- Server A does not update;
- Discord reports the failed server, update stage, and exit status.

### Reboot failure

After all regular updates succeed, required reboots run one at a time.

If any server does not return online within the configured timeout:

- all remaining reboots stop immediately;
- Server B and Server A do not update or reboot;
- Discord reports which server failed to return and that the run was halted.

## Final order

```text
1. Update all regular servers, 5 minutes apart.
2. Stop immediately if any update fails.
3. Reboot only regular servers that require it, 10 minutes apart.
4. Stop immediately if any rebooted server fails to return.
5. Update Server B second-last, only if updates exist.
6. Reboot Server B only if required.
7. Update Server A last, only after Server B completes.
8. Reboot Server A last, only if required.
```

Discord sends a message whenever:

- a server begins updating;
- a server finishes updating;
- a server is already current;
- a server begins rebooting;
- a server returns after reboot;
- an update fails and the run stops;
- a reboot fails and the run stops;
- Server B is unavailable;
- Server A is unavailable and Server B takes over;
- the complete run finishes.

## Coordinator setup

Suggested:

```text
Server A: falfa.kori.cat — 10.10.0.8
Server B: laika.kori.cat — 10.10.0.7
SSH port: 2222
```

Install this project on both coordinator servers.

```bash
sudo ./install.sh
```

On Server A, use the defaults in `sample.env`.

On Server B:

```bash
COORDINATOR_ROLE="B"
COORDINATOR_NAME="laika.kori.cat"
COORDINATOR_IP="10.10.0.7"
PEER_NAME="falfa.kori.cat"
PEER_IP="10.10.0.8"
```

Both coordinators require their SSH public key on every server.

```bash
ssh-copy-id -i /root/.ssh/nekonet-autoupdate.pub -p 2222 root@10.10.0.2
```

Enable on both:

```bash
sudo systemctl enable --now nekonet-autoupdate.timer
```

## Important limitation

A two-coordinator design can still face an ambiguous network partition where each coordinator can reach targets but not the other coordinator. Per-target locks reduce duplicate work, but a third witness is required for strict split-brain prevention.

Test this on non-critical servers before enabling it across production.
