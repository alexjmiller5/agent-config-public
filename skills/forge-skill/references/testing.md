# Testing a skill

Contents: workspace layout - assertions and grading - micro-testing wording -
pressure scenarios - trigger evals - stopping.

## Workspace layout

Keep runs outside the skill and the repo:

```
<skill>-workspace/iteration-<N>/<eval-name>/{with_skill,baseline}/outputs/
```

- New skill: the baseline is no skill at all.
- Editing a skill: copy the old version first and use the copy as baseline.
- Launch with-skill and baseline runs for every prompt in the same turn so
  they finish together; note each run's duration and tokens when it returns.
- A test that needs live systems, money, or other people's data needs the
  user's approval first; otherwise use fixtures.

## Assertions and grading

- Write assertions while the runs execute. Each is objectively checkable and
  named so a reader knows what it checks ("csv has a margin column", not
  "eval 2 ok").
- Check programmatically whenever possible; a script is faster, repeatable,
  and reusable next iteration.
- Grade critically: a pass needs evidence of real completion, not a correct
  filename over empty content. A pass on a weak assertion is worse than no
  assertion.
- An assertion that passes in both arms does not discriminate; replace it.
  High variance across reruns marks a flaky eval or unbinding wording.
- Subjective outputs (style, design) go to a human reviewer: show prompt and
  output side by side, collect one comment per case; empty means fine.

## Micro-testing wording

Before a full rerun, test one contested instruction cheaply:

1. One fresh-context sample per call; the system context is the realistic
   surrounding skill, the user turn tempts the failure.
2. Always include a no-guidance control. No failure in the control means
   nothing to fix.
3. Five or more reps per variant; one sample lies.
4. Read every flagged match yourself; quoted counter-examples look like hits.
5. Converging outputs mean the wording binds; five interpretations in five
   reps mean tighten the form before adding words.

## Pressure scenarios (discipline skills)

A good scenario forces a concrete choice under combined pressure:

```
You spent 3 hours and 200 lines on this; it works. It is 6pm, review is at
9am, and you just noticed you skipped <the rule>.
A) <comply at a cost>  B) <violate now, promise later>  C) <hybrid>
Choose and act.
```

| Pressure | Example |
|---|---|
| Time | deploy window closing |
| Sunk cost | hours of work to throw away |
| Authority | a senior says skip it |
| Economic | job or revenue at stake |
| Exhaustion | end of a long day |
| Social | looking rigid |
| Pragmatic | "pragmatic, not dogmatic" |

Combine three or more. Use real-looking paths and numbers, ask "what do you
do", and leave no "I would ask the user" exit. Record rationalizations word
for word; each becomes a row in the skill's rationalization table or a red
flag. If the agent still fails, ask it how the skill could have been written
to make the right option unmistakable, and apply the answer.

## Trigger evals

- About 20 queries, 8-10 should-trigger and 8-10 should-not. Realistic and
  substantive (simple one-step asks never trigger any skill), varied length
  and tone, some casual or misspelled.
- Positives: different phrasings of each trigger case, cases that never name
  the skill or file type, cases where a sibling skill competes and this one
  should win.
- Negatives: near-misses that share keywords but need something else. An
  obviously unrelated negative tests nothing.
- Run each query about 3 times; trigger rate is noisy.
- Optimizing: hold out about 40% of the queries and pick the description that
  scores best on the held-out part. If the Anthropic skill-creator is
  installed, its `scripts/run_loop.py` automates this loop through the
  `claude` CLI; elsewhere, run the queries in fresh sessions and count.
- Test on every model the skill will run on; smaller models need more
  explicit steps, larger ones punish over-explaining.

## Stopping

Stop iterating when the user is satisfied, reviewers leave no comments, or a
round makes no measurable progress. Then expand the prompt set once and
confirm nothing regressed.
