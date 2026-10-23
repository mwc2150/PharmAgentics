<!-- Markdown copy of the Google Doc "Evaluation Pack - 10/21" (Briefing Agent Evaluation Pack), taken 2026-10-23. The Google Doc is the master; update it first (change rule: pack first, then the specs that cite it). -->

# Briefing Agent Evaluation Pack

Oct 14, 2026 (updated Oct 21) · @Michael

## How to read this pack

This pack defines how the Weekly Brand-Performance Briefing Agent will be judged: what we measure, on which cases, against which ground truth and baselines. It is v0, a design with no code; results are added for the executed pack due Dec 4.

- **Part A, evaluation design:** what is measured, on which cases, against which baselines.
- **Part B, execution plan:** how the evaluation runs; each piece depends on an open item.
- **Part C, open items:** every unresolved decision, grouped by who resolves it. A note like (Open item 4) in Parts A and B points here.

**Scope.** Briefing Agent only. The Forecast-Explanation Agent is a separate use case with its own evaluation.

**Black-box rule.** Every eval item scores the brief and its evidence, given a seeded week. No item depends on the model, framework or orchestration. Component-level tests belong in each component spec's tasks.md.

**Links to other docs.** *Briefing Agent Personas* say what matters, through question IDs P1-Q1 to P4-Q6; this pack says how each is measured. Component specs cite eval item IDs (EV-x.y) in their Success Criteria.

**Course floor.** The course catalog sets four success criteria for this agent, and everything else builds on them:

1. Ten weeks of generated briefings, scored for factual accuracy.
2. Narrative numbers reconciled with source tables.
3. A failure-mode catalog.
4. A cost and time comparison with manual work.

**Change rules.**

- The quality dimensions table (Section 1) is a source of truth; every change goes in its change log.
- Pack first: change an eval item here, then the specs that cite it.
- Targets can be set or tightened until held-out results are seen, and never loosened after.
- Held-out cases stay closed during development and open only at check-ins.

## Part A. Evaluation design

Sections 1 to 6 define the evaluation: the quality dimensions, eval items, test cases, ground-truth labels and baselines.

### 1. Quality dimensions (source of truth)

Nine dimensions organize every eval item. Eight come from grouping the 24 persona questions by what we would measure; Governance covers needs that no question raises.

| Dimension | What it asks | Persona questions |
| :- | :- | :- |
| Numeric fidelity | Does every number in the brief match the pinned data version? | P1-Q1, P3-Q6 |
| Data reliability | Are data problems caught and separated from real business change? | P1-Q2, P2-Q1 |
| Detection and prioritization | Are material changes found, noise left out, and changes ranked by business impact? | P1-Q3, P1-Q5, P3-Q1, P3-Q2 |
| Explanation | Are competing drivers tested, the right one named, and the change located? | P2-Q2, P2-Q4, P4-Q1, P4-Q2, P4-Q4 |
| Calibration | Does stated confidence match the evidence, with abstention when evidence is weak? | P2-Q3, P4-Q5 |
| Traceability | Does every claim link to the evidence that produced it? | P1-Q4, P2-Q5 |
| Communication and action | Is the brief plain, continuous with prior weeks, and clear on next steps? | P3-Q3, P3-Q4, P3-Q5, P4-Q3, P4-Q6 |
| Efficiency and value | Does the brief save analyst time at acceptable cost without credibility risk? | P1-Q6, P2-Q6 |
| Governance | Does the brief protect individuals, use governed terms, and respect data boundaries? | None; from the personas' core needs and meeting notes, and the Proposal's risks |

The archetype labels in the Personas doc stay as persona-facing framing. This table is the authoritative grouping for evaluation. Change log: Oct 21, 2026, P4 (Marketer) questions added to Explanation, Calibration, and Communication and action; eval items EV-4.5 and EV-7.5 added.

### 2. Traceability matrix

Every persona question is measured by at least one eval item. Items are named here and defined in Section 3; the last five rows cover needs with no question.

| Question | In short | Measured by |
| :- | :- | :- |
| P1-Q1 | Do the numbers tie out to the source tables? | Numeric reconciliation; Factual accuracy |
| P1-Q2 | Is the data complete; which cuts can't I report? | Artifact catch rate; Unreliable-cut handling; Refresh-window handling |
| P1-Q3 | Which changes are big enough to make the brief? | Null-week false alarms; Priority agreement |
| P1-Q4 | Where did this number come from? | Evidence coverage; Link resolution; Time to trace |
| P1-Q5 | Was anything material left out? | Material-event recall |
| P1-Q6 | How much do I rewrite before it goes up? | Edit burden; Time and cost; Run limits |
| P2-Q1 | Is this change real, or a data or calendar artifact? | Artifact catch rate; Artifact vs. real labeling |
| P2-Q2 | Which explanations were considered, and why ruled out? | Driver attribution; Alternatives tested; Compound weeks |
| P2-Q3 | How confident are we; where do we say we don't know? | Confidence calibration; Abstention; Overclaiming; Limit handling |
| P2-Q4 | Where is the change concentrated? | Concentration |
| P2-Q5 | Can I show the evidence behind a challenged claim? | Evidence coverage; Link resolution |
| P2-Q6 | Does this free time without risking credibility? | Time and cost; Critical error rate; Run-to-run stability; Run limits |
| P3-Q1 | What changed this week that I need to know? | Material-event recall; Priority agreement |
| P3-Q2 | Does it matter, or can I ignore it? | Null-week false alarms; Calendar handling |
| P3-Q3 | Why did it happen, in terms I can repeat upward? | Plain-language explanation |
| P3-Q4 | Is this new or continuing; better or worse? | Continuity; Restatement disclosure |
| P3-Q5 | What should I do, and who do I loop in? | Next steps; No individual identification |
| P3-Q6 | Can I quote these numbers in leadership meetings? | Numeric reconciliation; Restatement disclosure |
| P4-Q1 | Did my campaign move brand sales, and by how much? | Driver attribution; Promotion verdicts; Concentration |
| P4-Q2 | Which geographies, segments and channels responded? | Concentration; Promotion context |
| P4-Q3 | Did the campaign reach the people it was meant to reach? | Promotion context (partly; reach data is Open item 19) |
| P4-Q4 | Is the lift real, or access, a competitor or the season? | Promotion verdicts; Alternatives tested; Calendar handling; Compound weeks |
| P4-Q5 | How confident is the estimate; when will we know more? | Confidence calibration; Abstention; Continuity |
| P4-Q6 | Where should the next dollar go? | Next steps; No individual identification |
| Core needs (P1, P3) | Same Monday format, short, every week | Format conformance |
| HR guardrail (P2, P3, P4 notes) | No line identifies an individual rep | No individual identification |
| Terminology (scope note) | Governed metric terms; "competitive intelligence" | Governed terminology |
| Eval integrity | No component can read the answer key | Answer-key isolation |
| Data use (Proposal) | No proprietary or patient data to external tools | Data use |

### 3. Eval items

Thirty-seven eval items cover the nine dimensions. Each target is a proposal until confirmed with Dr. Admasu (Open item 1); "To set" means no value is proposed yet.

**Methods**

| Method | How it works |
| :- | :- |
| Auto | Code compares the brief and its evidence to the answer key or the pinned data |
| Human | A reviewer scores against a rubric, with the gold brief as reference (Open item 13) |
| Judge | An LLM judge scores, only after its agreement with human labels is measured (Open item 2) |
| Review | A one-time process check, not run per case |

#### Numeric fidelity

| ID | Eval item | How it is scored | Method | Target |
| :- | :- | :- | :- | :- |
| EV-1.1 | Numeric reconciliation | Share of numbers in the brief that match the value computed from the pinned data version, after stated rounding; only the pinned version counts, not whichever version is newest | Auto | Set % against the run's pinned data version; hard gate |
| EV-1.2 | Restatement disclosure | On seeded restatement cases, the brief states that a number reported last week changed, with old and new values | Auto | 100% of seeded cases |
| EV-1.3 | Factual accuracy | Non-numeric claims (direction, metric, cut, timing) checked against the answer key and pinned data | Human | To set |

#### Data reliability

| ID | Eval item | How it is scored | Method | Target |
| :- | :- | :- | :- | :- |
| EV-2.1 | Artifact catch rate | Share of injected data artifacts (restatement, coverage drop, duplicate load, missing or late week) flagged in the data-health section | Auto | ≥ 90% |
| EV-2.2 | Artifact vs. real labeling | Each reported change labeled as data artifact, calendar effect or real change, against the answer key; confusion matrix reported | Auto | To set |
| EV-2.3 | Unreliable-cut handling | When a cut fails validation, its numbers are suppressed or visibly qualified | Auto | 100% |
| EV-2.4 | Refresh-window handling | When the data window moves forward a week, weeks restated inside the refresh window are flagged; none is silently overwritten or double-counted (Open item 18) | Auto | 100% |

#### Detection and prioritization

| ID | Eval item | How it is scored | Method | Target |
| :- | :- | :- | :- | :- |
| EV-3.1 | Material-event recall | Share of seeded material events surfaced in the brief | Auto | ≥ 90% |
| EV-3.2 | Null-week false alarms | Changes reported as material in weeks with no injected event | Auto | ≤ 1 per null week |
| EV-3.3 | Priority agreement | Order of reported changes against answer-key business impact (Auto) and the gold brief's top items (Human) | Auto, Human | To set |
| EV-3.4 | Calendar handling | Holiday and plan-year-reset weeks recognized and not reported as business events | Auto | To set |

#### Explanation

| ID | Eval item | How it is scored | Method | Target |
| :- | :- | :- | :- | :- |
| EV-4.1 | Driver attribution | Leading driver named for each story matches the injected driver; confusion matrix across driver types | Auto | ≥ 70% top-1 on single-event weeks |
| EV-4.2 | Alternatives tested | Each story records the competing explanations considered, each with a verdict and evidence; a reviewer checks they are the sensible ones | Auto, Human | To set |
| EV-4.3 | Concentration | Stated concentration (region, payer channel, specialty) matches where the event sits; segment contributions sum to the total change | Auto | To set |
| EV-4.4 | Compound weeks | In two-event or masked weeks, both causes are found or the interaction is flagged; no single-cause over-attribution | Auto, Human | Reported |
| EV-4.5 | Promotion verdicts | On seeded cases with and without a promotion change, the promotion hypothesis gets the right verdict: supported when promotion drove the change, ruled out when another driver did. Promotion is never credited in a week where it was not injected | Auto | To set |

#### Calibration

| ID | Eval item | How it is scored | Method | Target |
| :- | :- | :- | :- | :- |
| EV-5.1 | Confidence calibration | Correctness rate per stated confidence level; higher levels must be right more often (Open item 3) | Auto | Reported by level |
| EV-5.2 | Abstention | Abstains ("investigate next") on cases built to be ambiguous, and not when evidence is strong; both directions reported | Auto | To set |
| EV-5.3 | Overclaiming | Causal language ("driven by") appears only where the evidence supports it | Judge | To set |
| EV-5.4 | Limit handling | Every story that reaches the investigation round or stall limit closes as "unresolved, investigate next" or is flagged; none closes with an unsupported driver (Open item 17) | Auto | 100% |

#### Traceability

| ID | Eval item | How it is scored | Method | Target |
| :- | :- | :- | :- | :- |
| EV-6.1 | Evidence coverage | Share of claims linked to at least one evidence item | Auto | 100% of numeric claims; others to set |
| EV-6.2 | Link resolution | Every link opens the output that produced the value, on the pinned data version, so a later challenge is answered against the numbers as they stood at sign-off | Auto | 100% |
| EV-6.3 | Time to trace | Reviewer minutes to find a sampled claim's source | Human | Reported against the manual baseline |

#### Communication and action

| ID | Eval item | How it is scored | Method | Target |
| :- | :- | :- | :- | :- |
| EV-7.1 | Plain-language explanation | Could a brand director repeat this explanation upward? Rubric informed by ASD-STE100 (short sentences, one word with one meaning), paired with business framing for tone | Human, Judge | To set |
| EV-7.2 | Continuity | For multi-week events, the brief says whether a change is new or continuing, and whether it is improving or worsening | Auto, Human | To set |
| EV-7.3 | Next steps | Each open story names what to investigate next and which function (market access, sales, finance, marketing) to involve, where relevant | Human | To set |
| EV-7.4 | Format conformance | The brief follows the agreed Monday template and length (Open item 4) | Auto | To set |
| EV-7.5 | Promotion context | For each story where promotion was tested, the brief shows promotion activity for the same cut and weeks next to performance, and states what the data cannot show yet, such as reach | Auto, Human | To set |

#### Efficiency and value

| ID | Eval item | How it is scored | Method | Target |
| :- | :- | :- | :- | :- |
| EV-8.1 | Edit burden | Share of claims edited or removed, and reviewer minutes, before the brief could go to the manager | Human | Reported against the manual baseline |
| EV-8.2 | Time and cost | Run time, reviewer minutes and dollars per brief, against timed gold-brief writing | Auto, Human | Reported (course floor) |
| EV-8.3 | Critical error rate | Share of briefs with at least one error that would mislead leadership: wrong number, wrong driver at high confidence, missed top event, or false alarm in the top three | Auto | To set |
| EV-8.4 | Run-to-run stability | Spread across repeated runs of the same case, in stories reported and drivers named | Auto | Reported |
| EV-8.5 | Run limits | Every run stays within set limits on investigation rounds, run time and brief length, so time, cost and draft size stay predictable (Open item 17) | Auto | 100% of runs |

#### Governance

| ID | Eval item | How it is scored | Method | Target |
| :- | :- | :- | :- | :- |
| EV-9.1 | No individual identification | Rep-level activity (calls, vacancies) is aggregated or suppressed so no line points to one person, including promotion results read by marketing; tested on seeded rep-vacancy cases (Open item 5) | Auto, Judge | 100% |
| EV-9.2 | Governed terminology | Wording matches metric definitions ("new patients" only for NBRx, never NRx); "competitive intelligence," not "statistical surveillance" | Auto, Judge | 100% |
| EV-9.3 | Answer-key isolation | No component can read the answer key; only the eval harness can (Open item 10) | Auto | 100% |
| EV-9.4 | Data use | No proprietary or patient data sent to external tools, checked against the data inventory | Review | 100% |

### 4. Test case design

Each test case is a (seed, week) pair from the synthetic brand world, with expected outcomes taken from the answer key.

**Case taxonomy**

| Category | What it tests | Example events | Dimensions tested |
| :- | :- | :- | :- |
| Real business events | The brief finds and explains genuine change | Access restriction on a major plan, competitor launch, rep vacancy, promotion change with or without a sales effect, 30- to 90-day conversion | Detection, Explanation, Calibration, Governance |
| Data artifacts | Data problems are caught before interpretation | Restatement, panel coverage drop, duplicate load, missing or late week | Numeric fidelity, Data reliability |
| Calendar effects | Expected seasonal moves are not alarmed on | Thanksgiving and Christmas weeks, January plan-year reset | Data reliability, Detection |
| Null weeks | Nothing is reported when nothing happened | No injected event | Detection, Efficiency |
| Compound weeks | Interactions and over-attribution | Two events in one region, such as a promotion push in the same week as an access change; a real event masked by an artifact | Explanation, Calibration |
| Multi-week events | Continuity across briefs | An event that persists or decays over several weeks | Communication and action |
| Stress cases | Behavior under failure (course calendar, Oct 30) | Missing data; inconsistent sources; unsupported questions (Open item 14) | Numeric fidelity, Data reliability |

The event types are what the generator must be able to produce. Field names follow the shared data dictionary, not this pack, and driver category labels are still open (Open item 9).

**Case format**

Every case is written as Given / When / Then, so it pastes straight into a spec's acceptance scenarios.

| Field | Content |
| :- | :- |
| Case ID | Stable ID, e.g. C-012 |
| Category | One category from the taxonomy |
| Seed, week | Generator seed and the brief's reporting week |
| Split | Dev or held-out |
| Given | Injected events active that week, from the answer key |
| When | The brief runs on the pinned data version for that week |
| Then (must say) | Expected stories, drivers, concentration and confidence range |
| Must not say | Claims or phrases that fail the case |
| Eval items | IDs of the eval items the case exercises |

**Worked example (illustrative)**

- **Given** seed S, week W, and a prior authorization added on a major commercial plan in one region, effective the week before.
- **When** the brief runs for week W.
- **Then** it reports an NBRx decline concentrated in that region and the commercial channel. It names the access change as the leading driver at high or medium confidence, and records promotion and competitor explanations as ruled out, with evidence.
- **Must not say** that a competitor launch drove the decline, or call NRx "new patients."
- **Eval items** EV-3.1, EV-4.1, EV-4.2, EV-4.3, EV-5.1, EV-9.2.

### 5. Answer-key schema

The answer key records what really happened in each seeded week: one record per injected event. It is stored apart from the data, and only the eval harness reads it (EV-9.3). Its exact format is still to be agreed with the Forecast team (Open item 8).

| Field | Content |
| :- | :- |
| Event ID | Stable ID for the injected event |
| Event type | One event from the case taxonomy (Section 4) |
| Affected cut | Metric, geography, payer channel and HCP specialty |
| Start week | First week the event affects the data |
| Magnitude | Size of the injected effect |
| Duration or decay | How long the effect lasts and how it fades |
| Label | Real event, data artifact or calendar effect |

### 6. Baselines

Every version of the brief runs on the same cases and is scored by the same eval items, so each comparison is like with like.

| Version | What it is | Why it is compared |
| :- | :- | :- |
| Manual | Timed gold briefs (Section 7) | Cost and time comparison; quality ceiling |
| Scripted | Fixed pipeline with a fixed order of checks and a templated brief | Answers "is the agent really a script?" (Proposal risk) |
| Low-code | Low-code prototype of the same workflow | Proposal and course baseline |
| Custom agent | The Briefing Agent | System under test |

An ablation of the agent's autonomous steps will be added once the architecture is settled (Open item 16).

## Part B. Execution plan

Sections 7 to 9 set how the evaluation runs. Each depends on at least one open item in Part C.

### 7. Gold briefs and splits

- **Gold briefs.** Written blind from the tables, without the answer key, by someone who did not build the generator (Open item 6). Each is timed; that time is the manual baseline for Time to trace, Edit burden, and Time and cost. A subset gets two independent gold briefs, and their agreement sets the ceiling for human-scored items.
- **Splits.** Dev cases are used while building. Held-out cases are generated with parameters the builders do not see, and open only at check-ins (Open item 11).
- **Headline test.** A 10-week back-test on a held-out seed. The ten weeks are consecutive weekly data periods, not ten live runs.
- **Size.** About 40 dev and 15 held-out cases, with every taxonomy category in both splits (Open item 7).

### 8. Run protocol

- **Pinned data.** Each run pins one data version, and every score references it.
- **Reruns.** Each case runs five times; mean and spread are reported (Open item 15). Run-to-run variation is a finding, not noise to hide.
- **Held-out access.** Held-out cases open only at check-ins, and scores are logged before any change is made.
- **Scorecard.** One table of versions × dimensions, in the same layout at every check-in.
- **Failure catalog.** Every failed eval item and every analyst edit gets one failure tag (Open item 12). Proposed tags: data misread, wrong metric, wrong grain, missed event, false alarm, over-attribution, missed interaction, stale context, unsupported claim, numeric mismatch, governance breach, run error.

### 9. What each check-in must show

Dates follow the course calendar and may move.

| Date | Milestone | Evidence from this pack |
| :- | :- | :- |
| Oct 30 | Low-code demonstrations (mentor) | Low-code scores against a simple baseline on shared dev cases, including stress cases |
| Nov 23 | Check-in #1: baseline | Scripted vs. low-code scores on dev cases; failure catalog v1 |
| Nov 27 | Evaluation and feedback triage (mentor) | Comparative scorecard on fixed cases; failure taxonomy; Nov 23 feedback turned into new cases |
| Dec 4 | Full-model review (mentor) | Executed pack (v1): held-out results for every version |
| Dec 7 | Check-in #2: full model | Custom agent vs. both baselines on held-out cases |
| Dec 14 | Final presentation | 10-week held-out back-test; cost and time comparison; failure catalog, with one meaningful failure walked through |

## Part C. Open items and shared conventions

Nineteen decisions remain open, grouped by who resolves them.

### 10. Open items

**For mentor**

| # | Open item | Where |
| :- | :- | :- |
| 1 | Confirm the proposed targets and set the rest | Section 3 |
| 2 | Agreement bar an LLM judge must meet before it replaces human scoring | Section 3, Methods |
| 3 | Confidence scale the brief uses (e.g., high, medium, low) | Section 3, Calibration |
| 4 | Monday template and length a real brief team uses | Section 3, Communication and action |
| 5 | Minimum aggregation level for rep-level data | Section 3, Governance |
| 6 | Who writes the blind gold briefs | Section 7 |
| 7 | Case counts: about 40 dev and 15 held-out | Section 7 |
| 19 | Whether promotion attribution and reach are in scope for the weekly brief; until decided, P4-Q3 is only partly measured | Section 2; Section 3, Explanation and Communication and action |

**For forecast team (Alvin, Sienna)**

| # | Open item | Where |
| :- | :- | :- |
| 8 | Answer-key format | Section 5 |
| 9 | Driver category labels | Section 4 |
| 10 | Answer-key isolation as a shared rule | Section 3, Governance |
| 11 | Who generates held-out seeds, and whether the teams swap them | Section 7 |
| 12 | Failure tag list | Section 8 |

**For our team**

| # | Open item | Where |
| :- | :- | :- |
| 13 | Human rubric scale (Meets, Partly, Misses) and anchors for each item | Section 3, Methods |
| 14 | What an "unsupported question" means for a batch brief | Section 4 |
| 15 | Rerun count, weighed against cost | Section 8 |
| 16 | Ablation of the agent's autonomous steps, after the roadmap and operation flow are aligned | Section 6 |
| 17 | Limits on investigation rounds, stalls, run time and brief length | Section 3, Calibration; Efficiency and value |
| 18 | Length of the refresh window in which past weeks can be restated | Section 3, Data reliability |

### 11. Confirmed shared conventions

The Proposal commits both agents to these, so they need no further agreement:

- One shared synthetic data layer (Section 4).
- Scoring on held-out seeded cases (Section 7).
- Comparison against scripted and low-code baselines (Section 6).
- Every number traces to a tool output (Numeric reconciliation, Section 3).
- Targets set with Dr. Admasu (Section 3).
- No proprietary or patient data sent to external tools (Data use, Section 3).
