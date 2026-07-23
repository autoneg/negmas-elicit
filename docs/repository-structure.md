# Repository Structure

## Layout

```text
negmas-elicit/
├── src/negmas_elicit/         # the package
│   ├── __init__.py            # public API (re-exports everything in __all__)
│   ├── common.py              # small helpers (_loc/_scale/_upper, argmin/argmax/argsort)
│   ├── user.py                # User model + ElicitationRecord
│   ├── strategy.py            # EStrategy: deep-elicitation query strategies
│   ├── queries.py             # Query/Answer/Constraint types, next_query, possible_queries
│   ├── expectors.py           # Expector implementations (mean/max/min/balanced/aspiring)
│   ├── base.py                # BaseElicitor: the elicitor abstract base class
│   ├── baseline.py            # DummyElicitor, FullKnowledgeElicitor (baselines)
│   ├── pandora.py             # Pandora's-box (Baarslag & Gerding 2015) + practical strategies (Mohammad & Nakadai 2018)
│   ├── voi.py                 # value-of-information elicitors (2017/2018/2019)
│   ├── mechanism.py           # SAOElicitingMechanism (the end-to-end negotiation)
│   └── cli.py                 # the `negmas-elicit` command-line interface
├── tests/                     # pytest suite
│   ├── test_imports.py        # public API imports cleanly
│   ├── test_user.py           # User / Query / RangeConstraint / EStrategy units
│   ├── test_elicitation.py    # end-to-end: strategies, every elicitor, the mechanism
│   └── test_cli.py            # the CLI commands
├── docs/                      # this documentation (mkdocs-material)
├── papers/                    # the papers whose algorithms are implemented here
├── mkdocs.yml                 # documentation site configuration
└── pyproject.toml             # package metadata, dependencies, the CLI entry point
```

## How the pieces fit together

```text
                        SAOElicitingMechanism
                        (an SAOMechanism)
                    ┌───────────────┴───────────────┐
             opponent negotiator            elicitor  (a BaseElicitor)
             (e.g. LimitedOutcomes)          │
                                             ├── User          (true ufun + query cost)
                                             ├── EStrategy      (which deep query next)
                                             ├── Query/Answer/Constraint  (what is asked)
                                             ├── Expector       (Distribution -> scalar)
                                             └── opponent model (acceptance probabilities)
```

- A negotiation runs as usual (alternating offers). On each of its turns the
  **elicitor** decides — using its algorithm (`pandora.py` / `voi.py`) — whether the
  value of asking the **user** one more query exceeds the query **cost**.
- Unknown utilities are **probability distributions** (uniform intervals). The
  `EStrategy` narrows them; the `Constraint`s attached to each `Answer` encode what
  an answer tells you about the utility.
- The **Expector** turns a probabilistic utility into the single number the
  negotiator needs to compare offers.
- `SAOElicitingMechanism` wires all of this together and records per-session metrics
  in `elicitation_state`.

## Module reference

| Module | Public symbols |
|--------|----------------|
| `common` | `_loc`, `_locs`, `_scale`, `_upper`, `_uppers`, `argmax`, `argmin`, `argsort` |
| `user` | `User`, `ElicitationRecord` |
| `strategy` | `EStrategy` |
| `queries` | `Constraint`, `RangeConstraint`, `RankConstraint`, `ComparisonConstraint`, `MarginalNeutralConstraint`, `Answer`, `Query`, `QResponse`, `CostEvaluator`, `next_query`, `possible_queries` |
| `expectors` | `Expector`, `StaticExpector`, `MeanExpector`, `MaxExpector`, `MinExpector`, `BalancedExpector`, `AspiringExpector` |
| `base` | `BaseElicitor` |
| `baseline` | `DummyElicitor`, `FullKnowledgeElicitor` |
| `pandora` | `BasePandoraElicitor`, `PandoraElicitor`, `OptimalIncrementalElicitor`, `FullElicitor`, `RandomElicitor`, `MeanElicitor`, `BalancedElicitor`, `AspiringElicitor`, `PessimisticElicitor`, `OptimisticElicitor`, `FastElicitor`, `weitzman_index_uniform` |
| `voi` | `BaseVOIElicitor`, `VOIElicitor`, `VOIFastElicitor`, `VOINoUncertaintyElicitor`, `VOIOptimalElicitor`, `OQA` |
| `mechanism` | `SAOElicitingMechanism` |
| `cli` | `main`, `run_session` (the `negmas-elicit` command) |

## Development

```bash
uv sync --all-extras         # install with dev + docs extras
uv run pytest -q             # run the test suite
uv run mkdocs serve          # preview the docs at http://127.0.0.1:8000
uv run ruff check src tests  # lint
```
