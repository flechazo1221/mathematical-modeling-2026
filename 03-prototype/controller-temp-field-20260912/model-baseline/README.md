# Prescribed-temperature baseline

This directory contains the raw metrics, trajectories, and linear-call records
for the current baseline imported read-only from
`04-compute/src/formal_compute.py`. In Q2—Q4 its implementation assigns the
internal temperature to the interpolated chamber temperature at each step.
The comparison driver is the sibling `../run_protocol.py`; no source file
under `04-compute/` is copied or modified here.
