"""Command-line interface.

    python -m etdp run --input input.yaml --config config.yaml            # full approach
    python -m etdp run --input input.yaml --config config_ablation.yaml   # ablation
    python -m etdp baseline --input input.yaml --config config.yaml       # single-prompt baseline
    python -m etdp resume --run-id <id> [--config config.yaml]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config, load_input


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="etdp", description="Neuro-symbolic automation of the ETDP (Kundisch et al., 2022)")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("run", "baseline"):
        s = sub.add_parser(name)
        s.add_argument("--input", required=True)
        s.add_argument("--config", default="config.yaml")
        s.add_argument("--output-dir", default=None)
        s.add_argument("--run-id", default=None)
    r = sub.add_parser("resume")
    r.add_argument("--run-id", required=True)
    r.add_argument("--config", default=None)
    r.add_argument("--output-dir", default=None)
    args = p.parse_args(argv)
    try:
        if args.command == "baseline":
            from .baseline import run_baseline
            print(f"outputs: {run_baseline(load_config(args.config), load_input(args.input), args.output_dir, args.run_id).resolve()}")
            return 0
        from .pipeline import Pipeline
        if args.command == "run":
            pipe = Pipeline.create(load_config(args.config), load_input(args.input), args.output_dir, args.run_id)
        else:
            cfg = load_config(args.config) if args.config else None
            if cfg is None:
                load_config(None)   # loads .env; the configuration saved with the run is used
            pipe = Pipeline.resume(args.run_id, args.output_dir, cfg)
        state = pipe.run()
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 – details in run.log
        print(f"run failed: {exc}", file=sys.stderr)
        return 1
    print(f"status: {state.status}\noutputs: {Path(pipe.run_dir).resolve()}")
    return 0 if state.status in ("completed", "max_iterations_reached") else 1


if __name__ == "__main__":
    sys.exit(main())
