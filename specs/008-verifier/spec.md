# Feature Specification: Verifier (Stage 6)

**Feature Branch**: `008-verifier`
**Created**: 2026-10-16
**Status**: Draft
**Input**: Architecture §5.6, §10.2; Evaluation Pack EV-1.1, EV-5.3, EV-6.1, EV-9.1, EV-9.2; Personas P1-Q1, P1-Q4, P2-Q5, P3-Q6

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reject any wrong number (Priority: P1)

Before any reviewer sees a brief, the verifier checks every claim token, every digit and every rendered number against the pinned snapshot. A brief with a planted wrong number is rejected.

**Why this priority**: A single mismatched figure forces the analyst to re-audit the whole brief (P1-Q1).

**Independent Test**: Plant a wrong number in a rendered brief. Check the verifier rejects it and names the claim.

**Acceptance Scenarios**:

1. **Given** a draft where a token has no evidence item, **When** the verifier runs, **Then** it fails with the token named.
2. **Given** a digit that is not from a token, **When** the verifier runs, **Then** the brief fails.
3. **Given** a rendered number that differs from the pinned data after stated rounding, **When** the verifier runs, **Then** the brief fails with the claim and both values.
4. **Given** a number that matches the newest data but not the pinned snapshot, **When** the verifier runs, **Then** it fails. Only the pinned version counts.

---

### User Story 2 - Every claim has evidence (Priority: P1)

Every story cites at least one evidence item. Every link resolves to the tool output and span that produced the value, on the pinned snapshot.

**Why this priority**: A manager must show the evidence behind a challenged claim (P2-Q5).

**Independent Test**: Remove an evidence link. Check the verifier flags it. Follow every link in a good brief to its span.

**Acceptance Scenarios**:

1. **Given** a claim with no evidence ID, **When** the verifier runs, **Then** the claim is flagged.
2. **Given** a link, **When** it is followed, **Then** it opens the output on the pinned snapshot.

---

### User Story 3 - Governance checks (Priority: P1)

The verifier fails any line that identifies an individual rep, any banned term, and any wording that does not match the semantic layer.

**Why this priority**: The brief is forwarded to sales leadership. Terminology is a mentor directive.

**Independent Test**: Plant a rep name, "statistical surveillance", and "new patients" for NRx. Check each is caught.

**Acceptance Scenarios**:

1. **Given** a line that points to one rep, **When** the verifier runs, **Then** it fails.
2. **Given** a banned term, **When** the verifier runs, **Then** it fails.
3. **Given** "new patients" attached to NRx, **When** the verifier runs, **Then** it fails.

---

### User Story 4 - Overclaiming judge, used only when trusted (Priority: P2)

A judge checks faithfulness and causal wording: a causal word is allowed only for High-confidence stories. The judge scores briefs only after its agreement with human labels has been measured and meets the bar.

**Why this priority**: Overclaiming in front of leadership is the costliest error (P2-Q3). An unmeasured judge cannot be trusted.

**Independent Test**: Run the judge on human-labeled briefs. Report agreement. Plant a causal claim on a Medium story and check it is flagged.

**Acceptance Scenarios**:

1. **Given** a causal claim on a Medium or Low story, **When** the checks run, **Then** it is flagged.
2. **Given** a judge with agreement below the bar, **When** scoring is requested, **Then** the judge does not replace human scoring.

---

### User Story 5 - One revision, then visible flags (Priority: P1)

If a brief fails, the writer gets the flags and one revision. If it still fails, it goes to review with its flags visible.

**Why this priority**: The Monday brief is never blocked, and people see what failed.

**Independent Test**: Plant a failure the writer can fix, and one it cannot. Check the first passes after one revision and the second reaches review flagged.

**Acceptance Scenarios**:

1. **Given** a first-pass failure, **When** the verifier flags it, **Then** exactly one revision loop to the narrative stage runs.
2. **Given** a second failure, **When** the loop ends, **Then** the run state is VERIFICATION_FLAGGED and the flags appear to the reviewer.

### Edge Cases

- A claim is exact but the rounding rule is missing: the verifier fails it, not guesses.
- A glossary entry differs from the layer text: the verifier fails.
- A story's evidence exists, but only for a suppressed cut: the verifier flags it as unqualified use.
- The judge is unavailable: code checks still run, and the brief carries a note that the judge did not run.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The verifier MUST check that every claim token resolves to an evidence item.
- **FR-002**: The verifier MUST fail any digit that does not come from a token.
- **FR-003**: The verifier MUST reconcile every rendered number to the pinned snapshot after stated rounding, and MUST ignore any newer data.
- **FR-004**: The verifier MUST check that every story cites at least one evidence item.
- **FR-005**: The verifier MUST check that every evidence link resolves on the pinned snapshot to the output and span that produced the value.
- **FR-006**: The verifier MUST check wording against the semantic layer per metric.
- **FR-007**: The verifier MUST fail lines that identify an individual rep.
- **FR-008**: The verifier MUST fail banned terms, including "statistical surveillance", and "new patients" outside NBRx.
- **FR-009**: The verifier MUST check that causal wording appears only on High-confidence stories.
- **FR-010**: A judge MAY check faithfulness and overclaiming. It MUST NOT replace human scoring until its agreement with human labels is measured and meets the bar. [NEEDS CLARIFICATION: agreement bar (Evaluation Pack open item 2)]
- **FR-011**: On failure, the verifier MUST trigger exactly one revision loop to the narrative stage, then pass flags to review.
- **FR-012**: The verifier MUST record, for every claim, a verification status in `brief_claims`.
- **FR-013**: The verifier MUST be deterministic for all code checks.
- **FR-014**: The verifier MUST report the failure tag for each flag from the shared tag list.

### Key Entities

- **Verification result**: per-claim status, per-check result, flags.
- **Flag**: check name, claim, evidence, failure tag.
- **Judge result**: label, rationale, agreement stats.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The verifier rejects 100% of briefs with a planted wrong number (Architecture §14 criterion; EV-1.1 gate).
- **SC-002**: 100% of numeric claims link to at least one evidence item (EV-6.1).
- **SC-003**: Zero governance failures reach review unflagged (EV-9.1, EV-9.2).
- **SC-004**: Causal wording appears only where the evidence supports it, scored by judge and human (EV-5.3).
- **SC-005**: Judge-human agreement is measured and reported before the judge scores anything.
- **SC-006**: 100% of failing briefs get exactly one revision and then reach review with visible flags.

## Assumptions

- The verifier reads the rendered brief, `brief_claims`, the pinned snapshot and the semantic layer. It does not read the answer key.
- A false pass is worse than a false fail. Thresholds lean toward failing.
- The failure-tag list is shared with the Forecast team. Proposed tags: data misread, wrong metric, wrong grain, missed event, false alarm, over-attribution, missed interaction, stale context, unsupported claim, numeric mismatch, governance breach, run error.
