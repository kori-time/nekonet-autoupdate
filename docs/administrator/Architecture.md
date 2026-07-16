# Architecture

Coordinator A is preferred. Coordinator B is the failover peer. Both expose the same API model and use the same storage abstraction. Target updates are sequential and the workflow fails closed on the first unconfirmed operation.
