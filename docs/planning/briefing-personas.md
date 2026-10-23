<!-- Markdown copy of the Google Doc "Personas - 10/21" (Briefing Agent Personas), taken 2026-10-23. The Google Doc is the master; update it first. -->

# Briefing Agent Personas

Oct 14, 2026 (updated Oct 21) · @Michael

## Overview

Four personas anchor the Weekly Brand-Performance Briefing Agent, each defined by what they do with the brief: one produces it, one judges it, and two act on it. The Brand Director sets the promotion budget, and the Marketer spends it. All four care whether the brief is right; they differ in what they check and what they do next.

| ID | Persona | Relationship | Defining question | Proposal anchor |
| :- | :- | :- | :- | :- |
| P1 | Commercial Analyst | The producer; builds and ships the brief; first reviewer of agent output | Can I review this instead of rebuilding it? | The analyst workflow is the behavior modeled |
| P2 | Insights Manager | The gatekeeper; judges whether the story is real; signs off; owns adoption | Is this real, and can I put my name on it? | Brand analytics team is the decision owner |
| P3 | Brand Director | The decision-maker; reads the approved brief, acts on it, and sets the promotion budget | What changed, and what do I do about it? | Brand leadership is a named brief audience |
| P4 | Marketer | The executor; runs promotion with the budget P3 sets; reads the signed-off brief | Did my promotion move the brand, and where? | Another named brief audience; added at the mentor's request (Oct 21) |

P1 and P2 are the two analytics-team personas; P3 and P4 are brand-team readers. Question IDs (P1-Q1 to P4-Q6) are stable so later work can reference them.

---

## P1 · Commercial Analyst · Ace

### About

An analyst on the brand's Insights & Analytics team, typically 2 to 4 years in. Owns the Monday brief end to end today: pulls weekly Rx data (TRx, NRx, NBRx) and market share, refreshes the KPI tables, cuts by region, payer channel and HCP specialty, and drafts the commentary. Also answers return-on-investment questions about marketing spend from the brand team. Fluent in SQL, Python and Excel, and knows the data's quirks, but rarely has time to chase them. With the agent in place, P1 becomes its first reviewer every week.

### Motivations

- Ship the brief on time without a Sunday-night or early-Monday crunch.
- Spend time on analysis instead of refreshing tables.
- Be known for numbers that never need a correction.
- Grow into investigative and strategic work.

### Core Needs

- A draft that's already reconciled to the source tables, so review means reading, not rebuilding.
- Every number traceable to the query or tool that produced it, in one step.
- Data problems (late feed, restatement, coverage drop) surfaced before drafting, not discovered mid-draft.
- Output in the team's existing Monday format.
- Edits that are easy to make and get captured, so the same fix isn't needed next week.

### Pain Points / Central Questions - Validation, Quality, Decision, Tracing, Confidence, Time

| ID | Question | Pain behind it |
| :- | :- | :- |
| P1-Q1 | Do the numbers in this draft tie out to the source tables, or do I recheck every one? | One mismatched figure today means re-auditing the whole brief. |
| P1-Q2 | Is this week's data complete and on time, and if not, which cuts can't I report? | Late or partial feeds and restatements are often found after the draft is written. |
| P1-Q3 | Which changes are big enough to make the brief, and which are just noise? | Small territories swing wildly; deciding what to include is manual and inconsistent week to week. |
| P1-Q4 | Where did this number come from? | Tracing a figure back to its query takes longer than computing it. |
| P1-Q5 | Am I confident that nothing that's material in nature was left out? | The brief is judged on what it misses as much as on what it says. |
| P1-Q6 | How much do I have to rewrite before this goes to my manager? | If fixing the draft takes as long as writing it, the agent saves nothing. |

**Meeting notes**

- Narrative reconciliation: each run pins one data version as the source of truth, and the brief reconciles to it, not to whichever version the model happens to see (P1-Q1).
- Data refreshes: if for instance, the two-year window (Nov 2024 to Oct 2026) moves forward one week per run, the weeks restated inside the refresh window are flagged– never silently overwritten or double-counted (P1-Q2).
- Capping manager calls: a limit on the manager's round trips to the data-check loop keeps run time and the size of the draft predictable (P1-Q6).

---

## P2 · Insights Manager · Marcus

### About

Leads analytics for the brand and manages a small team of analysts. Reviews and signs off the brief, then sends it to other managers, the Brand Director and marketing, and owns the team's credibility with brand leadership. When a number moves, P2 uses domain knowledge of promotion and sales channels to decide whether it is real and backed by evidence, works with data vendors on restatements and coverage changes, and defends the explanation in brand meetings. P2 is the decision owner for adopting the agent.

### Motivations

- Never send leadership a story that later unravels.
- Be the trusted source on why the numbers moved, not just what they were.
- Move the team's time from repetitive reporting to higher-value analysis.
- Adopt AI in a way that holds up when leadership or compliance asks how it works.

### Core Needs

- Data artifacts separated from real business change before any explanation is offered.
- Competing explanations tested, with a record of what was ruled out and why.
- An honest confidence level, and an explicit "not enough evidence yet" when that is the truth.
- A breakdown of where a national change comes from: region, payer channel, specialty.
- An audit trail that can be opened on the spot when a claim is challenged.
- Nothing in the brief that identifies an individual rep's performance or employment status.

### Pain Points / Central Questions - Validation, Decision, Quality, Tracing, Confidence, Value

| ID | Question | Pain behind it |
| :- | :- | :- |
| P2-Q1 | Is this change real, or a data or calendar artifact? | Restatements, panel coverage changes and holiday weeks get misread as business events. |
| P2-Q2 | What explanations were considered, and why were the others ruled out? | Single-cause stories collapse the moment someone asks "what about the competitor launch?" |
| P2-Q3 | How confident are we, and where should we say we don't know yet? | Overclaiming in front of leadership costs more than saying "still investigating." |
| P2-Q4 | Where is the change concentrated? | A national number hides that one region, channel or specialty drives most of it. |
| P2-Q5 | If someone challenges a claim, can I show the evidence behind it? | Defending a number today means reconstructing the analyst's work after the fact. |
| P2-Q6 | Is this freeing my team's time without putting our credibility at risk? | A tool that saves hours but ships one wrong story a quarter is a net loss. |

**Meeting notes**

- HR guardrail: territory-level rep calls and rep vacancies can point to one person, so they are aggregated or suppressed before anything reaches the brief (Core Needs).
- Capping manager calls: round and stall limits on the manager's calls to the data-check loop bound cost and time; a story that hits the cap closes as "unresolved, investigate next" or is flagged (P2-Q3, P2-Q6).
- Narrative reconciliation: every claim's evidence points to the pinned data version, so a challenge is answered against the numbers as they stood at sign-off (P2-Q5).

---

## P3 · Brand Director · Diana

### About

Leads marketing and strategy for the brand and is accountable for performance against plan. Decides the promotion budget for HCP and consumer audiences and gives it to marketing (P4). Oversees the digital and sales reps who carry quotas. Reads the approved brief early in the week, often between meetings, and carries it into leadership updates and conversations with finance, market access and sales leadership. Not a data specialist: relies on the analytics team for the numbers and wants the "so what." P3 never touches the agent directly; they only see the output P2 has signed off.

### Motivations

- Catch problems early enough to act, such as an access restriction or a competitor launch.
- Walk into leadership meetings with a clear story that holds up under questions.
- Put promotion and field resources where they will move the brand.
- Avoid being surprised by a question about something they haven't heard yet.

### Core Needs

- The few changes that matter, ranked by business impact, at the top.
- Explanations in plain language, with confidence stated honestly.
- What is being investigated next, and who else needs to know.
- Numbers safe to repeat upward without a later correction.
- A short brief in the same format every week.

### Pain Points / Central Questions - Decision, Quality, Translatability, Tracing, Action, Confidence

| ID | Question | Pain behind it |
| :- | :- | :- |
| P3-Q1 | What changed this week that I need to know about? | Long reports bury the two things that matter. |
| P3-Q2 | Does this matter for the brand, or can I ignore it? | Seasonal dips and noise reported as crises cause alarm fatigue. |
| P3-Q3 | Why did it happen, in terms I can explain to my leadership? | Technical explanations don't translate upward. |
| P3-Q4 | Is this new, or the same issue we discussed last week, and is it getting better or worse? | Repeated alarms erode attention, and the trend across weeks gets lost. |
| P3-Q5 | What should I do, and who should I loop in? | Implications for market access, sales and finance are left implicit. |
| P3-Q6 | Can I quote these numbers in my leadership meeting? | One number corrected after the fact damages credibility upward. |

**Meeting notes**

- STE: reader-facing text and use-case documentation follow ASD-STE100 principles (short sentences, one word with one meaning); STE gives clarity, so pair it with business framing for tone (P3-Q3).
- Narrative reconciliation: when a restatement changes a number reported last week, the brief says so explicitly (P3-Q4, P3-Q6).
- HR guardrail: the brief is forwarded to sales leadership, so it carries no line that identifies an individual rep (P3-Q5).

---

## P4 · Marketer · Magdalena

### About

A brand marketer who runs promotion with the budget the Brand Director (P3) sets. Plans campaigns to HCPs and consumers across digital, email, paid media and field programs. Accountable for reach, so that campaigns are seen by tens of thousands of people, and for showing that promotion moved brand sales. Reads the brief only after P2 signs it off, and uses its findings in campaign reviews, decks and budget requests. Not a data specialist, but fluent in campaign metrics. P4 never touches the agent directly.

### Motivations

- Show that campaigns moved brand sales, not only impressions.
- Defend the budget with evidence at the next planning cycle.
- Learn which geographies, segments and channels respond, and move spend there.
- Catch an underperforming campaign early enough to fix it.

### Core Needs

- Promotion tested as one explanation among several, never assumed.
- Changes broken down by geography and channel, so a campaign's area can be compared with the rest.
- An honest confidence level, with the delay before a promotion effect can show stated plainly.
- Promotion activity shown next to brand performance for the same weeks.
- Findings P4 can take into the budget conversation with P3.

### Pain Points / Central Questions - Attribution, Concentration, Reach, Validation, Confidence, Action

| ID | Question | Pain behind it |
| :- | :- | :- |
| P4-Q1 | Did my campaign move brand sales, and by how much? | Sales gains are credited to whichever campaign launched last. |
| P4-Q2 | Which geographies, segments and channels responded, and which did not? | A metro-wide or national number hides that one borough or channel drives most of the effect. |
| P4-Q3 | Did the campaign reach the people it was meant to reach? | High impressions can hide low engagement in the target segment. |
| P4-Q4 | Is the lift real, or was it access, a competitor or the season? | Claiming credit for a formulary win damages credibility with P3. |
| P4-Q5 | How confident is the estimate, and when will we know more? | Promotion effects lag, so early reads are often too high or too low. |
| P4-Q6 | Where should the next dollar go? | Budget shifts are argued from anecdote, not evidence. |

**Meeting notes**

- Budget flow: P3 sets the promotion budget for HCP and consumer audiences and gives it to marketing. Digital and sales reps, such as HCP and PA reps, carry quotas and carry out part of the plan (P4-Q6).
- Sequencing: P4 receives the brief after P2 signs off. P2's knowledge of the channels decides which promotion findings are credible (P4-Q4).
- Example scope from the mentor: NY metro data over 3 to 4 months, with trends by borough and demographic segment, statistical models for promotion attribution by demographic, location and channel, and results delivered as decks and briefs. The weekly brief covers only part of this; see Scope Notes (P4-Q1, P4-Q2).
- Reach: campaigns are meant to be seen by tens of thousands of people (P4-Q3).
- HR guardrail: promotion results are reported by geography and channel, never by individual rep (P4-Q2, P4-Q6).

## Scope Notes

**Stakeholders left out on purpose.** Finance, market access and sales operations read or act on the brief's findings, but none of them shapes how it is built. Finance is the primary stakeholder of the Forecast-Explanation Agent. These groups appear here only as people P3 loops in (P3-Q5). Marketing was added as P4 on Oct 21, at the mentor's request.

**Marketer scope.** P4's user stories cover what P4 does with the brief, with basic data responses. The brief tests promotion as one possible driver of a change and reports what it finds, with a confidence level. It does not run promotion attribution or return-on-investment models. Campaign data beyond today's promo_activity table (channel spend, reach, borough demographics) waits on a decision with the forecast team and the mentor.

**Link to the evaluation pack.** These personas say what matters, in the users' words; they hold no metrics or thresholds. The evaluation pack should map every question ID to at least one evaluation case or rubric item. Some questions can be checked automatically (P1-Q1, P2-Q1); others need a human judge against the gold briefs (P1-Q6, P3-Q3).

**Terminology.** Per our mentor, use "competitive intelligence" instead of "statistical surveillance" in the brief and in every project document, including the Proposal and the operation flow.

**To-Do: Verify with mentor**

- [x] Do these four roles match how a brand team actually runs the Monday brief? **Yes!**
- [ ] What length and format does a real brief take for a reader like P3?
- [ ] Does sign-off sit with a manager like P2, or one level higher?
- [ ] Is promotion attribution in the weekly brief's scope, or only promotion as one tested driver?
- [ ] For the NY metro example, is borough-level geography a region inside the national data world, or a separate world?
