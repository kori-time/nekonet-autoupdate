# Safety

The state machine is fail closed. Invalid transitions raise errors. Failed runs are terminal and cannot resume without an explicit new run.
