# Getting Started

## Installation

### From PyPI

```bash
pip install negmas-elicit
```

### From Source

```bash
git clone https://github.com/yasserfarouk/negmas-elicit.git
cd negmas-elicit
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/yasserfarouk/negmas-elicit.git
cd negmas-elicit
pip install -e ".[dev,docs]"
```

## Basic Concepts

### User Model

The `User` class represents a human user with preferences over negotiation outcomes. Users can answer queries about their preferences with configurable accuracy and cost.

```python
from negmas_elicit import User

# Create a user with a utility function
user = User(
    ufun=my_utility_function,
    cost=0.01,  # Cost per query
)
```

### Elicitors

Elicitors are negotiators that can query users to learn about their preferences. The main elicitor types are:

- **PandoraElicitor**: Uses Pandora's box approach for optimal query selection
- **VOIElicitor**: Uses Value of Information theory
- **DummyElicitor**: No elicitation (baseline)
- **FullKnowledgeElicitor**: Assumes complete knowledge (baseline)

```python
from negmas_elicit import PandoraElicitor, VOIElicitor

# Create a Pandora-based elicitor
elicitor = PandoraElicitor(
    user=user,
    strategy=strategy,
)

# Create a VOI-based elicitor
voi_elicitor = VOIElicitor(
    user=user,
    strategy=strategy,
)
```

### Queries

Queries are questions asked to users to elicit their preferences:

- **RangeConstraint**: Ask about utility range for an outcome
- **ComparisonConstraint**: Compare two outcomes
- **RankConstraint**: Rank multiple outcomes
- **MarginalNeutralConstraint**: Find marginal neutral points

### Elicitation Strategy

The `EStrategy` class manages the elicitation process, tracking beliefs about user preferences and selecting queries.

```python
from negmas_elicit import EStrategy

strategy = EStrategy(
    outcomes=outcomes,
    queries=possible_queries(outcomes),
)
```

## Running an Elicitation Negotiation

```python
from negmas import make_issue
from negmas_elicit import (
    SAOElicitingMechanism,
    PandoraElicitor,
    User,
    EStrategy,
)

# Define the negotiation issues
issues = [
    make_issue(name="price", values=10),
    make_issue(name="quantity", values=5),
]

# Create mechanism
mechanism = SAOElicitingMechanism(
    issues=issues,
    n_steps=100,
)

# Create user and elicitor
user = User(ufun=utility_function, cost=0.01)
elicitor = PandoraElicitor(user=user)

# Add negotiators and run
mechanism.add(elicitor)
mechanism.add(opponent_negotiator)
mechanism.run()

# Get results
print(f"Agreement: {mechanism.agreement}")
print(f"Elicitation cost: {elicitor.elicitation_cost}")
```

## Next Steps

- See the [API Reference](api.md) for detailed documentation
- Check the [NegMAS documentation](https://negmas.readthedocs.io/) for more on negotiation mechanisms
