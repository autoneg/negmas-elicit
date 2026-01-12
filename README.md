# negmas-elicit

[![PyPI version](https://badge.fury.io/py/negmas-elicit.svg)](https://badge.fury.io/py/negmas-elicit)
[![Tests](https://github.com/yasserfarouk/negmas-elicit/actions/workflows/test.yml/badge.svg)](https://github.com/yasserfarouk/negmas-elicit/actions/workflows/test.yml)
[![Documentation](https://github.com/yasserfarouk/negmas-elicit/actions/workflows/docs.yml/badge.svg)](https://yasserfarouk.github.io/negmas-elicit/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

A library for preference elicitation during automated negotiations. This module was extracted from the [negmas](https://github.com/yasserfarouk/negmas) library to provide a focused, standalone package for elicitation capabilities.

## Features

- **Multiple Elicitation Strategies**: Pandora-based elicitors, Value of Information (VOI) elicitors, and baseline implementations
- **Query System**: Flexible query types including range, rank, comparison, and marginal neutrality constraints
- **User Modeling**: Simulate users with different response behaviors and costs
- **Expector Functions**: Various strategies for handling uncertainty (mean, max, min, balanced, aspiring)
- **Mechanism Integration**: `SAOElicitingMechanism` for running negotiations with preference elicitation

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

## Quick Start

```python
from negmas import MappingUtilityFunction
from negmas.outcomes import make_issue
from negmas_elicit import (
    User,
    PandoraElicitor,
    SAOElicitingMechanism,
)

# Define the negotiation issues
issues = [make_issue(10, "price"), make_issue(5, "quality")]

# Create a user with a known utility function
ufun = MappingUtilityFunction(
    mapping=lambda o: o[0] / 10 + o[1] / 5,
    issues=issues,
)
user = User(ufun=ufun, cost=0.1)

# Create an elicitor
elicitor = PandoraElicitor(user=user)

# Use in a mechanism or standalone elicitation
# ...
```

## Available Elicitors

### Baseline Elicitors
- `DummyElicitor`: No elicitation, uses prior beliefs
- `FullKnowledgeElicitor`: Assumes complete knowledge of user preferences

### Pandora Elicitors
- `PandoraElicitor`: Standard Pandora's box approach
- `OptimalIncrementalElicitor`: Optimal incremental elicitation
- `FastElicitor`: Fast approximation
- `MeanElicitor`, `BalancedElicitor`, `AspiringElicitor`: Different expectation strategies
- `OptimisticElicitor`, `PessimisticElicitor`: Optimistic/pessimistic strategies

### VOI Elicitors
- `VOIElicitor`: Value of Information based elicitation
- `VOIFastElicitor`: Fast VOI approximation
- `VOIOptimalElicitor`: Optimal VOI strategy
- `VOINoUncertaintyElicitor`: VOI without uncertainty modeling

## Documentation

Full documentation is available at [https://yasserfarouk.github.io/negmas-elicit/](https://yasserfarouk.github.io/negmas-elicit/)

## Requirements

- Python 3.12+
- negmas >= 0.10.0

## License

This project is licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See the [LICENSE](LICENSE) file for details.

## Citation

If you use this library in your research, please cite the negmas library:

```bibtex
@inproceedings{negmas2019,
  title={NegMAS: A Platform for Automated Negotiation},
  author={Mohammad, Yasser and Greenwald, Amy and Nakadai, Shinji},
  booktitle={International Conference on Principles and Practice of Multi-Agent Systems},
  pages={343--351},
  year={2019},
  organization={Springer}
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
