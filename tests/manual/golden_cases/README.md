# Golden cases

Golden cases preserve expert feedback as reusable judge-recall fixtures. One
`gc_<miEventId>_<slug>.md` file contains YAML frontmatter, the feedback verbatim,
and one or more `GC-xx` labels.

Required frontmatter: `mi_event_id`, `event_title`. Optional keys are
`scenario_group_id` and `artifacts`. Each label requires `type` (`A` event
contradiction, `B` external fact, `C` relevance/discriminativeness, `D` clarity),
`target`, `expected_judge`, and `지적`; `인용` is optional.

`--golden` runs the evaluator against the case artifacts and displays its judge
violations next to these labels. It does not decide semantic matches automatically.
After human review, pass a JSON record through `--golden-record` so the evaluator
stores matched, missed, and extra IDs in `golden_case_results`. Type B labels are
reported separately because they can require facts absent from supplied artifacts.

When a normal batch happens to include a golden `mi_event_id`, the report only
shows a notice. Use an explicit `--golden` run for recall scoring.
