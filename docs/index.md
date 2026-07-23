# negmas-elicit

**Preference elicitation for automated negotiation.**

`negmas-elicit` provides algorithms and tools for eliciting a user's preferences
*during* an automated negotiation, when querying the user is costly and the
negotiator must trade off the value of extra information against its cost. It was
extracted from the [NegMAS](https://github.com/yasserfarouk/negmas) library into a
focused, standalone package.

The package implements the elicitation algorithms from a line of research on
value-of-information based elicitation:

| Family | Algorithm | Reference |
|--------|-----------|-----------|
| Pandora's Box | `PandoraElicitor`, `OptimalIncrementalElicitor`, ... | [Baarslag & Gerding, *IJCAI 2015*](https://www.ijcai.org/Proceedings/15/Papers/008.pdf) |
| Value of Information | `VOIElicitor` (OQA) | Baarslag & Kaisers, *AAMAS 2017* |
| Fast VOI | `VOIFastElicitor` | Mohammad & Nakadai, *PRIMA 2018* |
| Optimal VOI | `VOIOptimalElicitor` | Mohammad & Nakadai, *AAMAS 2019* |

## Features

- **Many elicitors** — Pandora's-box elicitors, value-of-information (VOI) elicitors,
  and baselines (`DummyElicitor`, `FullKnowledgeElicitor`).
- **Query types** — range, comparison, ranking and marginal-neutrality constraints.
- **User modeling** — a `User` that answers queries with a configurable per-query cost.
- **Deep-elicitation strategies** — `EStrategy` (`bisection`, `titration`, `pingpong`, ...).
- **A ready-to-run mechanism** — `SAOElicitingMechanism` that plugs an elicitor into a
  standard alternating-offers negotiation and records rich per-session metrics.
- **A CLI** — `negmas-elicit` for running single sessions and full evaluation sweeps.

## Quick example

```python
from negmas_elicit import SAOElicitingMechanism

# Generate a random negotiation scenario (utilities, opponent, priors, ...)
config = SAOElicitingMechanism.generate_config(
    cost=0.02,  # what the user charges per query
    n_outcomes=10,
    n_steps=100,
    conflict=1.0,  # how opposed the two ufuns are (0..1)
    own_utility_uncertainty=0.2,  # how uncertain the elicitor's prior ufun is
    own_reserved_value=0.1,
    opponent_type="limited_outcomes",
)

# Plug a value-of-information elicitor into the negotiation and run it.
mech = SAOElicitingMechanism(
    **config, elicitor_type="voi", elicitation_strategy="bisection"
)
mech.run()

s = mech.elicitation_state
print("agreement       :", s["agreement"])
print("elicitor utility:", round(s["elicitor_utility"], 3))
print("elicitation cost:", round(s["elicitation_cost"], 3))
print("queries asked   :", s["n_queries"])
```

## Installation

```bash
pip install negmas-elicit
```

See [Getting Started](getting-started.md) for a guided tour, [Running Evaluations](evaluations.md)
for the CLI, [Repository Structure](repository-structure.md) for the layout, and the
[API Reference](api.md) for details.

## License

Licensed under the AGPL-3.0-or-later license.
