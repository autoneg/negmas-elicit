# Getting Started

## Installation

### From PyPI

```bash
pip install negmas-elicit
```

### From source (development)

```bash
git clone https://github.com/autoneg/negmas-elicit.git
cd negmas-elicit
pip install -e ".[dev,docs]"     # or: uv sync --all-extras
```

`negmas-elicit` requires Python 3.12+ and a recent `negmas` (>= 0.15).

## Core concepts

| Concept | Class | Role |
|---------|-------|------|
| User | `User` | Owns the *true* utility function and answers queries at a per-query `cost`. |
| Query strategy | `EStrategy` | Decides which "deep" query to ask next to narrow a utility estimate. |
| Query / Answer | `Query`, `Answer`, `Constraint` | A question, its possible answers, and the utility constraint each implies. |
| Elicitor | `PandoraElicitor`, `VOIElicitor`, ... | A negotiator that decides *when/whether* to query the user while negotiating. |
| Expector | `MeanExpector`, `BalancedExpector`, ... | Reduces a probabilistic utility (a `Distribution`) to a scalar for decisions. |
| Mechanism | `SAOElicitingMechanism` | An alternating-offers negotiation wired up with an elicitor + opponent. |

A utility that has not been fully elicited is represented as a **probability
distribution** over its possible values (a uniform interval `[loc, loc+scale]`).
Elicitation shrinks that interval; the `cost` charged per query is what makes
*asking less* worthwhile.

## The user

```python
from negmas import MappingUtilityFunction
from negmas_elicit import User

ufun = MappingUtilityFunction(
    {(0,): 0.1, (1,): 0.4, (2,): 0.2, (3,): 0.9, (4,): 0.6},
    reserved_value=0.0,
)
user = User(preferences=ufun, cost=0.02)  # 0.02 charged per query

user.ufun((3,))  # 0.9  -> the true value
user.cost_of_asking()  # 0.02
user.total_cost  # 0.0  -> grows as it is queried
```

## Elicitation strategies

`EStrategy` performs *deep* elicitation: it repeatedly narrows the utility of a
single outcome. The named strategies map to how the estimate interval is split:

- `"exact"` — one query returns the exact value.
- `"bisection"` — halve the interval each query.
- `"titration+step"` / `"titration-step"` — move a bound by a fixed `step`.
- `"pingpong"` — alternate tightening the lower and upper bound.

```python
from negmas.sao import SAOMechanism
from negmas_elicit import EStrategy, User
from negmas import MappingUtilityFunction

neg = SAOMechanism(outcomes=[(i,) for i in range(5)], n_steps=20)
user = User(
    preferences=MappingUtilityFunction({(i,): 0.1 * i for i in range(5)}), cost=0.02
)

strategy = EStrategy(strategy="bisection", resolution=1e-3)
strategy.on_enter(nmi=neg.shared_nmi)

value, response = strategy.apply(user=user, outcome=(3,))
# `value` is either a float (fully elicited) or a Distribution with .loc/.scale
```

## Running a full elicitation negotiation

### Option A — build the scenario yourself

```python
from negmas import MappingUtilityFunction
from negmas.preferences import IPUtilityFunction
from negmas.sao import SAOMechanism, LimitedOutcomesNegotiator
from negmas_elicit import User, EStrategy, PandoraElicitor

outcomes = [(i,) for i in range(5)]
ufun = MappingUtilityFunction(
    dict(zip(outcomes, [0.1, 0.4, 0.2, 0.9, 0.6])), reserved_value=0.0
)

neg = SAOMechanism(outcomes=outcomes, n_steps=20)

# the user + elicitor
user = User(preferences=ufun, cost=0.02)
strategy = EStrategy(strategy="bisection")
strategy.on_enter(nmi=neg.shared_nmi)
elicitor = PandoraElicitor(strategy=strategy, user=user)

# an opponent that only accepts a couple of outcomes
opponent = LimitedOutcomesNegotiator(
    acceptable_outcomes=[(3,), (4,)], acceptance_probabilities=[1.0, 1.0]
)

neg.add(opponent)
# the elicitor joins with a *prior* (uncertain) utility function
neg.add(elicitor, preferences=IPUtilityFunction(outcomes=outcomes, reserved_value=0.0))
neg.run()

print("agreement:", neg.agreement)
print("elicitation cost:", round(elicitor.elicitation_cost, 3))
```

### Option B — let the mechanism generate the scenario

`SAOElicitingMechanism.generate_config` builds a random-but-controlled scenario
(true utilities, opponent, priors) from high-level knobs; you then pick the
elicitor. This is the entry point used by the evaluation CLI and the papers'
experiments.

```python
from negmas_elicit import SAOElicitingMechanism

config = SAOElicitingMechanism.generate_config(
    cost=0.02,
    n_outcomes=10,
    n_steps=100,
    conflict=1.0,
    own_utility_uncertainty=0.2,
    own_reserved_value=0.1,
    opponent_type="limited_outcomes",
)
mech = SAOElicitingMechanism(
    **config, elicitor_type="voi", elicitation_strategy="bisection"
)
mech.run()

print(mech.elicitation_state["elicitor_utility"], mech.elicitation_state["n_queries"])
```

`elicitation_state` is a dict recorded at the end of every session; see
[Running Evaluations](evaluations.md) for the full list of metrics.

## Choosing an elicitor

| `elicitor_type` | Class | Notes |
|-----------------|-------|-------|
| `full_knowledge` | `FullKnowledgeElicitor` | Knows the true ufun — an upper baseline. |
| `pandora`, `fast`, `mean`, `balanced`, `optimistic`, `pessimistic` | Pandora's-box family | Query when the expected gain beats the cost. |
| `voi`, `voi_fast` | `VOIElicitor`, `VOIFastElicitor` | Value-of-information elicitation. |
| `voi_optimal` | `VOIOptimalElicitor` | Optimal value-of-information elicitation. |

## Next steps

- [Running Evaluations](evaluations.md) — reproduce the paper-style experiments with the CLI.
- [API Reference](api.md) — every public class and function.
