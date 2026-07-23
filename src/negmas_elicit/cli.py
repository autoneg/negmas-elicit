"""Command-line interface for running preference-elicitation evaluations.

The CLI drives `SAOElicitingMechanism` -- the same machinery used in the papers
this package accompanies -- to reproduce their *experimental methodology*: a
sweep over elicitor strategies and negotiation parameters (cost of asking,
utility uncertainty, conflict, number of outcomes, ...) collecting the utility
achieved by the elicitor, its elicitation cost, the number of queries asked and
the distance to the Pareto frontier.

Commands:
    negmas-elicit list                 list the available elicitors and strategies
    negmas-elicit run       [options]  run a single elicitation session
    negmas-elicit evaluate  [options]  sweep elicitors x repetitions and tabulate

Run ``negmas-elicit <command> --help`` for the options of each command.
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass

import numpy as np

from negmas_elicit.mechanism import SAOElicitingMechanism

#: The elicitor types understood by ``SAOElicitingMechanism(elicitor_type=...)``.
ELICITOR_TYPES: tuple[str, ...] = (
    "dummy",
    "full_knowledge",
    "full",
    "random",
    "pandora",
    "fast",
    "mean",
    "balanced",
    "optimistic",
    "pessimistic",
    "voi",
    "voi_fast",
    "voi_optimal",
)

#: The deep-elicitation query strategies understood by `EStrategy`.
STRATEGIES: tuple[str, ...] = (
    "exact",
    "bisection",
    "pingpong",
    "titration+0.05",
    "titration-0.05",
    "dtitration+0.05",
    "dtitration-0.05",
)

#: Metrics extracted from ``elicitation_state`` for reporting, in display order.
METRICS: tuple[str, ...] = (
    "elicitor_utility",
    "welfare",
    "elicitation_cost",
    "n_queries",
    "pareto_distance",
    "agreed",
    "steps",
    "total_time",
)


@dataclass
class SessionResult:
    """The outcome of a single elicitation session (a subset of ``elicitation_state``)."""

    elicitor: str
    agreement: object
    elicitor_utility: float
    opponent_utility: float
    welfare: float
    elicitation_cost: float
    n_queries: int | None
    pareto_distance: float | None
    agreed: bool
    steps: int
    total_time: float
    total_voi: float | None


def run_session(
    elicitor_type: str,
    *,
    cost: float = 0.02,
    n_outcomes: int = 10,
    n_steps: int = 100,
    conflict: float = 1.0,
    winwin: float = 0.0,
    own_utility_uncertainty: float = 0.2,
    own_reserved_value: float = 0.1,
    opponent_type: str = "limited_outcomes",
    strategy: str | None = "bisection",
    dynamic_queries: bool = True,
    seed: int | None = None,
) -> SessionResult:
    """Run a single elicitation negotiation and return its metrics.

    Args:
        elicitor_type: One of `ELICITOR_TYPES`.
        cost: The cost the user charges per elicitation query.
        n_outcomes: Number of outcomes in the (single-issue) negotiation.
        n_steps: Maximum number of negotiation rounds.
        conflict: Conflict level between the two utility functions in ``[0, 1]``.
        winwin: Win-win level in ``[0, 1]``.
        own_utility_uncertainty: Uncertainty (scale) of the elicitor's prior ufun.
        own_reserved_value: The elicitor's reserved value.
        opponent_type: The opponent negotiator type (e.g. ``"limited_outcomes"``,
            ``"tough"``, ``"aspiration"``).
        strategy: The deep-elicitation strategy (ignored / may be ``None`` for the
            VOI-optimal elicitor which chooses queries directly).
        dynamic_queries: Whether the query set is generated dynamically.
        seed: Optional seed making the generated scenario reproducible.

    Returns:
        A `SessionResult` with the metrics collected from ``elicitation_state``.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    config = SAOElicitingMechanism.generate_config(
        cost=cost,
        n_outcomes=n_outcomes,
        n_steps=n_steps,
        conflict=conflict,
        winwin=winwin,
        own_utility_uncertainty=own_utility_uncertainty,
        own_reserved_value=own_reserved_value,
        opponent_type=opponent_type,
    )
    kwargs: dict = dict(elicitor_type=elicitor_type, dynamic_queries=dynamic_queries)
    if strategy is not None and "optimal" not in elicitor_type:
        kwargs["elicitation_strategy"] = strategy
    mechanism = SAOElicitingMechanism(**config, **kwargs)
    mechanism.run()
    s = mechanism.elicitation_state
    return SessionResult(
        elicitor=elicitor_type,
        agreement=s.get("agreement"),
        elicitor_utility=float(s.get("elicitor_utility") or 0.0),
        opponent_utility=float(s.get("opponent_utility") or 0.0),
        welfare=float(s.get("welfare") or 0.0),
        elicitation_cost=float(s.get("elicitation_cost") or 0.0),
        n_queries=s.get("n_queries"),
        pareto_distance=s.get("pareto_distance"),
        agreed=bool(s.get("agreed")),
        steps=int(s.get("steps") or 0),
        total_time=float(s.get("total_time") or 0.0),
        total_voi=s.get("total_voi"),
    )


def _add_common_scenario_args(parser: argparse.ArgumentParser) -> None:
    """Add the scenario-defining options shared by ``run`` and ``evaluate``."""
    parser.add_argument("--cost", type=float, default=0.02, help="cost per query")
    parser.add_argument("--n-outcomes", type=int, default=10, help="number of outcomes")
    parser.add_argument("--n-steps", type=int, default=100, help="max negotiation rounds")
    parser.add_argument("--conflict", type=float, default=1.0, help="conflict level [0,1]")
    parser.add_argument("--winwin", type=float, default=0.0, help="win-win level [0,1]")
    parser.add_argument(
        "--uncertainty",
        type=float,
        default=0.2,
        dest="own_utility_uncertainty",
        help="elicitor prior utility uncertainty [0,1]",
    )
    parser.add_argument(
        "--reserved-value",
        type=float,
        default=0.1,
        dest="own_reserved_value",
        help="elicitor reserved value",
    )
    parser.add_argument(
        "--opponent",
        default="limited_outcomes",
        dest="opponent_type",
        help="opponent negotiator type",
    )
    parser.add_argument(
        "--strategy",
        default="bisection",
        choices=STRATEGIES,
        help="deep-elicitation query strategy",
    )


def _cmd_list(_args: argparse.Namespace) -> int:
    """Handle ``negmas-elicit list``."""
    print("Available elicitor types:")
    for name in ELICITOR_TYPES:
        print(f"  - {name}")
    print("\nAvailable elicitation strategies:")
    for name in STRATEGIES:
        print(f"  - {name}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    """Handle ``negmas-elicit run``."""
    result = run_session(
        args.elicitor,
        cost=args.cost,
        n_outcomes=args.n_outcomes,
        n_steps=args.n_steps,
        conflict=args.conflict,
        winwin=args.winwin,
        own_utility_uncertainty=args.own_utility_uncertainty,
        own_reserved_value=args.own_reserved_value,
        opponent_type=args.opponent_type,
        strategy=args.strategy,
        seed=args.seed,
    )
    print(f"Elicitor           : {result.elicitor}")
    print(f"Agreement          : {result.agreement}")
    print(f"Agreed             : {result.agreed}")
    print(f"Elicitor utility   : {result.elicitor_utility:.4f}")
    print(f"Opponent utility   : {result.opponent_utility:.4f}")
    print(f"Welfare            : {result.welfare:.4f}")
    print(f"Elicitation cost   : {result.elicitation_cost:.4f}")
    print(f"Queries asked      : {result.n_queries}")
    print(f"Pareto distance    : {result.pareto_distance}")
    print(f"Steps              : {result.steps}")
    print(f"Total time (s)     : {result.total_time:.4f}")
    if result.total_voi is not None:
        print(f"Total VOI          : {result.total_voi}")
    return 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    """Handle ``negmas-elicit evaluate`` (the sweep)."""
    import pandas as pd

    elicitors = args.elicitors or list(ELICITOR_TYPES)
    rows: list[dict] = []
    for elicitor in elicitors:
        for rep in range(args.repetitions):
            try:
                result = run_session(
                    elicitor,
                    cost=args.cost,
                    n_outcomes=args.n_outcomes,
                    n_steps=args.n_steps,
                    conflict=args.conflict,
                    winwin=args.winwin,
                    own_utility_uncertainty=args.own_utility_uncertainty,
                    own_reserved_value=args.own_reserved_value,
                    opponent_type=args.opponent_type,
                    strategy=args.strategy,
                    seed=(args.seed + rep) if args.seed is not None else None,
                )
            except Exception as e:  # keep the sweep going, report the failure
                print(f"[warn] {elicitor} rep {rep} failed: {e}", file=sys.stderr)
                continue
            rows.append(
                {"elicitor": elicitor, "rep": rep, **{m: getattr(result, m) for m in METRICS}}
            )

    if not rows:
        print("No successful sessions.", file=sys.stderr)
        return 1

    df = pd.DataFrame(rows)
    if args.raw is not None:
        df.to_csv(args.raw, index=False)
        print(f"Wrote raw per-session results to {args.raw}")

    summary = (
        df.drop(columns=["rep"])
        .groupby("elicitor", sort=False)
        .agg(["mean", "std"])
    )
    # keep the requested metric order
    summary = summary.reindex(columns=[(m, a) for m in METRICS for a in ("mean", "std")])
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 50)
    print(
        f"\nElicitation evaluation "
        f"(n_outcomes={args.n_outcomes}, cost={args.cost}, "
        f"uncertainty={args.own_utility_uncertainty}, "
        f"conflict={args.conflict}, reps={args.repetitions})\n"
    )
    print(summary.round(4).to_string())
    if args.out is not None:
        summary.round(6).to_csv(args.out)
        print(f"\nWrote summary to {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="negmas-elicit",
        description="Run preference-elicitation negotiations and evaluations.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list available elicitors and strategies")
    p_list.set_defaults(func=_cmd_list)

    p_run = sub.add_parser("run", help="run a single elicitation session")
    p_run.add_argument(
        "--elicitor", default="voi", choices=ELICITOR_TYPES, help="elicitor type"
    )
    _add_common_scenario_args(p_run)
    p_run.add_argument("--seed", type=int, default=None, help="random seed")
    p_run.set_defaults(func=_cmd_run)

    p_eval = sub.add_parser(
        "evaluate", help="sweep elicitors over repetitions and tabulate metrics"
    )
    p_eval.add_argument(
        "--elicitors",
        nargs="+",
        choices=ELICITOR_TYPES,
        default=None,
        help="elicitor types to compare (default: all)",
    )
    p_eval.add_argument(
        "--repetitions", type=int, default=10, help="sessions per elicitor"
    )
    _add_common_scenario_args(p_eval)
    p_eval.add_argument("--seed", type=int, default=0, help="base random seed")
    p_eval.add_argument("--out", default=None, help="write the summary table to CSV")
    p_eval.add_argument(
        "--raw", default=None, help="write raw per-session results to CSV"
    )
    p_eval.set_defaults(func=_cmd_evaluate)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``negmas-elicit`` console script."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
