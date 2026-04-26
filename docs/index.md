# negmas-elicit

**Preference elicitation module for automated negotiation**

`negmas-elicit` provides algorithms and tools for eliciting user preferences during automated negotiations. It was extracted from the [NegMAS](https://github.com/yasserfarouk/negmas) library to provide a focused, lightweight package for preference elicitation research and applications.

## Features

- **Multiple Elicitation Strategies**: Pandora-based elicitors, VOI (Value of Information) elicitors, and baseline approaches
- **Query Types**: Support for comparison, ranking, range, and marginal neutrality queries
- **User Modeling**: Flexible user models with configurable accuracy and response costs
- **Expector Functions**: Various strategies for estimating expected utility values
- **Integration with NegMAS**: Seamlessly works with NegMAS negotiation mechanisms

## Quick Example

```python
from negmas import make_issue, SAOMechanism
from negmas_elicit import SAOElicitingMechanism, PandoraElicitor, User

# Create a simple negotiation scenario
issues = [make_issue(name="price", values=10)]
mechanism = SAOElicitingMechanism(issues=issues, n_steps=100)

# Create a user with preferences
user = User(...)

# Create an eliciting negotiator
elicitor = PandoraElicitor(user=user)

# Add to mechanism and run
mechanism.add(elicitor)
mechanism.run()
```

## Installation

```bash
pip install negmas-elicit
```

## License

This project is licensed under the AGPL-3.0-or-later license.
