#!/usr/bin/env python3
"""
run.py — Single local run of the MaxwellABP Brownian sim.

Builds the `sim` binary (unless --no-build), materializes one input JSON from a
base config plus any `--<key> value` overrides, runs the simulation locally, and
collects everything under

    local/output/maxabp_run_<tag>/
        maxabp_run_<tag>_seed<seed>.h5      trajectory (HDF5)
        maxabp_run_<tag>_seed<seed>.json    the exact input config used
        maxabp_run_<tag>_seed<seed>.out     captured sim stdout/stderr
        log.json                            run metadata

The override mechanism (allowed keys, type casting, value validation) is shared
with psweep.py — run.py imports it directly so the two stay in lockstep.

Examples:

    # Smoke test: short run, small system, into local/output/maxabp_run_smoke/
    ./run.py --tag smoke --t_end 0.05 --N 64 --phi 0.4

    # Resolve + print the merged config without running anything.
    ./run.py --tag smoke --list-only

    # Active Brownian, soft-sphere, a specific seed, skip the rebuild.
    ./run.py --tag abp --Pe 20 --delta 0.9 --potential soft_sphere \
        --seed 7 --no-build

Any allowlisted Config field can be overridden with `--<key> <value>`
(see psweep.py --info, or the Configuration-Reference wiki page). `seed` and
`output_file` are owned by run.py: use --seed for the former; the output path is
always auto-named under the run directory.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

# Reuse psweep.py's override parsing + build helpers (it is import-safe: all of
# its executable logic is guarded by `if __name__ == "__main__"`).
from psweep import (
    parse_overrides,
    load_base_json,
    build_binary,
    REPO_ROOT,
    DEFAULT_BINARY,
    DEFAULT_BASE,
)

# run.py owns these two fields; they must not be passed as --<key> overrides.
RESERVED_OVERRIDES = {
    "seed":        "use the dedicated --seed flag",
    "output_file": "the output path is auto-named under the run directory",
}

DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "local", "output")


def make_parser():
    p = argparse.ArgumentParser(
        prog="run.py",
        description="Single local run of the MaxwellABP Brownian sim.",
        epilog=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--tag", type=str, required=True,
                   help="Short tag identifying this run "
                        "(output dir: maxabp_run_<tag>).")
    p.add_argument("--seed", type=int, default=0,
                   help="RNG seed; appears in the output filenames (default: 0).")
    p.add_argument("--base", type=str, default=DEFAULT_BASE,
                   help=f"Base input JSON (default: {DEFAULT_BASE}).")
    p.add_argument("--out-dir", type=str, default=DEFAULT_OUT_DIR,
                   help=f"Root output directory (default: {DEFAULT_OUT_DIR}).")

    build = p.add_argument_group("Build")
    build.add_argument("--no-build", action="store_true",
                       help="Skip the cmake/make step (use the existing binary).")
    build.add_argument("--build-type", type=str, default="Release",
                       help="CMAKE_BUILD_TYPE (default: Release).")

    p.add_argument("--list-only", action="store_true",
                   help="Resolve and print the merged config, then exit "
                        "without writing files or running the simulation.")
    return p


def reject_reserved(unknown):
    """Raise if the leftover args contain a run.py-owned key."""
    for tok in unknown:
        key = tok.lstrip("-").split("=", 1)[0]
        if key in RESERVED_OVERRIDES:
            raise ValueError(
                f'"--{key}" cannot be set as an override: '
                f"{RESERVED_OVERRIDES[key]}."
            )


def main():
    parser = make_parser()
    known, unknown = parser.parse_known_args()

    reject_reserved(unknown)
    overrides = parse_overrides(unknown)

    run_name = f"maxabp_run_{known.tag}"
    run_dir = os.path.join(known.out_dir, run_name)

    # ---- Resolve the merged config (base + overrides + owned fields) --------
    cfg = load_base_json(known.base, overrides)
    cfg["seed"] = int(known.seed)
    h5_path = os.path.join(run_dir, f"{run_name}_seed{known.seed}.h5")
    cfg["output_file"] = h5_path

    input_json = os.path.join(run_dir, f"{run_name}_seed{known.seed}.json")
    stdout_log = os.path.join(run_dir, f"{run_name}_seed{known.seed}.out")

    if known.list_only:
        print(f"Run:    {run_name}  (dry run, no files written)")
        print(f"  base      : {os.path.abspath(known.base)}")
        print(f"  seed      : {known.seed}")
        print(f"  run_dir   : {run_dir}")
        print(f"  output_h5 : {h5_path}")
        if overrides:
            print(f"  overrides : {overrides}")
        print("\nResolved config:")
        print(json.dumps(cfg, indent=2))
        return 0

    # ---- Build (auto unless --no-build) ------------------------------------
    if not known.no_build:
        build_binary(known.build_type)
    if not os.path.exists(DEFAULT_BINARY):
        raise FileNotFoundError(
            f"Binary not found at {DEFAULT_BINARY}. Re-run without --no-build, "
            f"or build manually:\n"
            f"  cmake -S . -B build -DCMAKE_BUILD_TYPE=Release\n"
            f"  cmake --build build -j --target sim"
        )

    # ---- Materialize the run directory + input JSON ------------------------
    os.makedirs(run_dir, exist_ok=True)
    with open(input_json, "w") as f:
        json.dump(cfg, f, indent=2)

    # ---- Run the simulation, capturing output ------------------------------
    cmd = [DEFAULT_BINARY, "run", input_json]
    print(f"Running: {' '.join(cmd)}")
    print(f"  (stdout/stderr -> {stdout_log})")

    start = time.monotonic()
    with open(stdout_log, "w") as log:
        proc = subprocess.run(cmd, stdout=log,
                              stderr=subprocess.STDOUT, text=True)
    wall_time = time.monotonic() - start

    success = proc.returncode == 0

    # ---- Write run metadata ------------------------------------------------
    log = {
        "run_name":       run_name,
        "tag":            known.tag,
        "date":           datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
        "command":        cmd,
        "base_json":      os.path.abspath(known.base),
        "binary":         os.path.abspath(DEFAULT_BINARY),
        "overrides":      overrides,
        "resolved_config": cfg,
        "seed":           int(known.seed),
        "output_h5":      h5_path,
        "input_json":     input_json,
        "stdout_log":     stdout_log,
        "return_code":    proc.returncode,
        "wall_time_sec":  round(wall_time, 3),
        "success":        success,
    }
    with open(os.path.join(run_dir, "log.json"), "w") as f:
        json.dump(log, f, indent=2)

    if success:
        print(f"\nDone in {wall_time:.2f}s. Output: {run_dir}")
        print(f"  trajectory : {h5_path}")
        print(f"  log        : {os.path.join(run_dir, 'log.json')}")
    else:
        print(f"\nSimulation FAILED (exit {proc.returncode}). "
              f"See {stdout_log}", file=sys.stderr)

    return 0 if success else proc.returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
