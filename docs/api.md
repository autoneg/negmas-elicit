# API Reference

Everything documented here is importable directly from `negmas_elicit`
(e.g. `from negmas_elicit import VOIElicitor`).

## Mechanism

::: negmas_elicit.SAOElicitingMechanism
    options:
      show_root_heading: true
      heading_level: 3

## User model

::: negmas_elicit.User
    options:
      show_root_heading: true
      heading_level: 3

::: negmas_elicit.ElicitationRecord
    options:
      show_root_heading: true
      heading_level: 3

## Elicitation strategy

::: negmas_elicit.EStrategy
    options:
      show_root_heading: true
      heading_level: 3

## Queries and constraints

::: negmas_elicit.Query
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.Answer
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.QResponse
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.Constraint
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.RangeConstraint
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.ComparisonConstraint
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.RankConstraint
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.MarginalNeutralConstraint
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.CostEvaluator
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.next_query
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.possible_queries
    options: { show_root_heading: true, heading_level: 3 }

## Elicitors

### Base class

::: negmas_elicit.BaseElicitor
    options: { show_root_heading: true, heading_level: 3 }

### Baseline elicitors

::: negmas_elicit.DummyElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.FullKnowledgeElicitor
    options: { show_root_heading: true, heading_level: 3 }

### Pandora's-box elicitors

::: negmas_elicit.BasePandoraElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.PandoraElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.OptimalIncrementalElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.FullElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.RandomElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.MeanElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.BalancedElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.AspiringElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.PessimisticElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.OptimisticElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.FastElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.weitzman_index_uniform
    options: { show_root_heading: true, heading_level: 3 }

### Value-of-information elicitors

::: negmas_elicit.BaseVOIElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.VOIElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.VOIFastElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.VOINoUncertaintyElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.VOIOptimalElicitor
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.OQA
    options: { show_root_heading: true, heading_level: 3 }

## Expectors

::: negmas_elicit.Expector
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.StaticExpector
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.MeanExpector
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.MaxExpector
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.MinExpector
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.BalancedExpector
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.AspiringExpector
    options: { show_root_heading: true, heading_level: 3 }

## Command-line interface

::: negmas_elicit.cli.run_session
    options: { show_root_heading: true, heading_level: 3 }

::: negmas_elicit.cli.main
    options: { show_root_heading: true, heading_level: 3 }
