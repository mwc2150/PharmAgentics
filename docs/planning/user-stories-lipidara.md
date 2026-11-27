<!-- DRAFT for Michael: the Lipidara (BXC) counterpart of docs/planning/user-stories.md, written 2026-11-27 from the repo's release (day1-v1, seed 7).
     Copy it into the master Google Doc "User stories" (or a sibling doc) when it has been read; until then the Google Doc has no Lipidara stories.
     Every figure below was computed by SQL over the governed reporting views (the same SQL sits in the facts of eval/golden/briefing/BXC-*.yaml); none comes from a system's output. -->

# **PharmAgentics User Stories: Briefing personas, Lipidara (BXC)**
Draft, Nov 27, 2026 · for @Michael
This doc has one user story per Briefing persona question for Lipidara (product code BXC): 24 stories, BXC-P1-Q1 to BXC-P4-Q6, one for each of P1-Q1 to P4-Q6 in the Cardiovela (BXA) stories. Each story is anchored on a real week or event in Meghna's release and says what the agent should answer, in Given / When / Then form, and what the persona does next. Where Lipidara has no fitting event, the story is anchored on a quiet week or an absence, and the correct answer is "nothing material" or "unresolved."
## **How to read a story**
Every story has the same six parts as the Cardiovela stories: Story, Answer from the data, Given / When / Then, Must not say, Action, Eval items.
**Assumptions first.** Every story states its definition up front, and every figure is computed under exactly that definition: the stated period (the question's weeks), the stated comparison weeks (the four weeks before unless the story names others), the territories counted (like for like means the territories whose feed passes the gate in every week compared), and holiday weeks left out of a period. A figure with no stated window is one week.
**Where the numbers come from.** The release (day1-v1, seed 7) loaded into DuckDB with Meghna's loader, then queried through reporting.v_weekly_rx_kpis, reporting.v_reportable_rx and reporting.v_feed_health. Cuts that fail the feed gate are left out. Dimensions, the calendar, promotion, inventory and access tables are read from the raw schema for context only. Weeks are named by their Monday start date. No answer key was used; the hidden answer key is not in the repo. Shares are Lipidara's TRx over the four-brand basket's TRx on the cuts that pass the gate.
**These are illustrations, not agent output.** Where the data shows no driver, the story says so instead of guessing.
## **What the data shows for Lipidara**
Lipidara has few events of its own in the release. Its formulary position never changes (tier 3 on every plan in every month), it has no promotion lapse and no supply shortfall, and most of its territory swings are weekly noise or a feed artifact. What the release does hold for Lipidara:
- **Metacora (BXE) launched 2026-03-02.** Lipidara's share of the four-brand basket fell from 35.4% (the four weeks before launch) to about 29% by late September; Metacora reached about 15%.
- **Three feed artifacts**, shared with every brand: Mid-Atlantic withheld for restatement review (2026-04-06), New England incomplete (2026-05-04), Great Lakes duplicate keys (2026-07-06). The one restatement in the release is logged against Cardiovela, not Lipidara.
- **Holiday weeks**, shared with every brand.
- **One plan-level rise that is a competitor's event.** Cardiovela moved to tier 3 with prior authorization and step therapy on one Mid-Atlantic Medicare Part D plan from 2025-08-01 to 2025-10-31; Lipidara's TRx on that plan rose.
- **A South Central gap with no driver** (June to July 2026).
- **Cardiovela events that are not Lipidara's** (Pacific supply, the Great Lakes and Southeast coverage gaps) do not touch Lipidara's own tables; two stories show the brief correctly leaving them out.
# **Part A. Briefing Agent personas, Lipidara (BXC)**
## **P1 · Commercial Analyst (Ace)**
Ace produces the brief and reviews the agent's draft first. Ace's stories test whether review can replace rebuilding.
### **BXC-P1-Q1 · Do the numbers tie out to the source tables?**
*As Ace, I want every figure in the draft to match the pinned data, so that I review the brief instead of rebuilding it.*
  - **Answer from the data (week of 2026-07-06).** The Great Lakes feed has 143 rows against 128 expected: 15 duplicate keys. Summed raw, Great Lakes BXC TRx is 615; with duplicates removed it is 583, so a naive sum overstates it by 32 TRx (5.5%). The gate withholds the whole Great Lakes cut, so national BXC TRx from reportable cuts is 3,373 across 7 of 8 territories.
  - **Given** the snapshot pinned for 2026-07-06 holds 15 duplicate Rx keys in Great Lakes. **When** the Lipidara (BXC) brief runs. **Then** every KPI figure matches the gated view on that snapshot, Great Lakes shows as withheld, and national figures carry the label "7 of 8 territories."
  - **Must not say** "Great Lakes BXC TRx was 615," or quote 3,373 as a full national total.
  - **Action.** Ace opens two claim links at random, confirms the withheld cut, and asks P2 to request a clean reload. No table is rebuilt.
  - **Eval items** EV-1.1, EV-2.1, EV-2.3.
### **BXC-P1-Q2 · Is this week's data complete, and which cuts can't I report?**
*As Ace, I want feed problems found before drafting, so that I never write commentary on numbers that are wrong.*
  - **Answer from the data (week of 2026-05-04).** New England delivered 84 of 128 rows (44 missing keys), panel coverage 0.656 against a 0.98 floor, 10.29 days after week end against a 7-day target; status INCOMPLETE. Its observed BXC TRx of 214 compares with 365 to 404 in the four weeks before. Projected from its panel coverage, New England is about 326 (214 divided by 0.656), an assumption the brief labels as projected, and projected national BXC TRx is 4,277. The other seven territories pass.
  - **Given** New England fails the feed gate for 2026-05-04. **When** the Lipidara (BXC) brief runs. **Then** the Bottom line says first that New England's feed is incomplete; The numbers gives a projected national with New England labelled as projected, an assumption from its panel coverage; What the data can't tell us names New England as not reportable with its reasons; every like-for-like figure states how many territories it covers; and no story is opened for New England.
  - **Must not say** "New England BXC fell 45%."
  - **Action.** Ace leaves New England out of the commentary and adds it to next week's re-check list. The brief tells Ace to re-run New England when the reload lands and to disclose the restated week.
  - **Eval items** EV-2.1, EV-2.3, EV-1.1.
### **BXC-P1-Q3 · Which changes are big enough to make the brief?**
*As Ace, I want normal territory swings left out, so that the brief is consistent week to week and nobody chases noise.*
  - **Answer from the data (week of 2025-04-14).** National BXC TRx was 4,590, 2.6% below its 4-week average. Territories swung widely: Mid-Atlantic up 29.6% week over week, South Central down 23.0%, Southeast down 17.9% and Northwest down 16.4%. Those swings are normal here: before Metacora launched, outside holiday weeks, a territory moved more than 15% in a week in 15.3% to 27.1% of weeks. No Lipidara access change sits in that week (there is none in the whole release) and BXC inventory fill was 0.970 or higher in every territory.
  - **Given** a week with no injected event and normal territory noise. **When** the Lipidara (BXC) brief runs. **Then** it is a routine brief: KPI table, no stories, at most one line that territory swings stayed in their normal range.
  - **Must not say** "Mid-Atlantic surged 30%."
  - **Action.** Ace ships the routine brief in minutes. The brief tells Ace nothing needs investigating.
  - **Eval items** EV-3.2, EV-3.3.
### **BXC-P1-Q4 · Where did this number come from?**
*As Ace, I want one click from any figure to the query behind it, so that tracing takes seconds, not an afternoon.*
  - **Answer from the data (weeks of 2025-08-04 to 2025-10-27).** Take the claim "BXC new-to-brand prescriptions on one Mid-Atlantic Medicare Part D plan rose 44%." It comes from the gated Rx view for plan SYN_MID_ATLANTIC_MEDICARE_PART_D_1: 28.3 NBRx a week over 12 weeks (Labor Day week left out), against 19.7 a week over the 9 weeks before (2025-06-02 to 2025-07-28). The cause cited beside it comes from access_status_monthly, and it belongs to a competitor: Cardiovela (BXA) moved on that plan from tier 2 to tier 3 and added prior authorization and step therapy, effective 2025-08-01. Lipidara's own tier on the plan stayed at 3.
  - **Given** a story that cites a plan-level NBRx change and a competitor's access change. **When** Ace clicks either number. **Then** it opens an evidence item naming the tool, its parameters (plan, product, weeks), the pinned snapshot and the trace span.
  - **Must not say** a figure with no evidence link.
  - **Action.** Ace checks the link instead of re-querying. Reviewer minutes to trace are logged against the manual baseline.
  - **Eval items** EV-6.1, EV-6.2, EV-6.3.
### **BXC-P1-Q5 · Am I confident nothing material was left out?**
*As Ace, I want every material change surfaced and ranked, so that the brief is not judged on what it missed.*
  - **Answer from the data (week of 2026-06-08).** National BXC TRx was 3,894, 6.4% below its average for the four weeks before (2026-05-11 to 2026-06-01), on all 8 territories. One story was live: competitor Metacora (BXE), launched 2026-03-02, held 12.5% of the basket and was still climbing, while Lipidara's share was 31.4%, against 35.4% in the four weeks before launch. The one territory worth checking, Pacific, is not a Lipidara story: Pacific BXC TRx was 626, 3.7% below its previous four weeks, with BXC inventory fill 0.975.
  - **Given** a week with one live competitor story and one territory that looks worth checking. **When** the Lipidara (BXC) brief runs. **Then** the Metacora story appears, and the "considered and dropped" list shows Pacific supply as checked and not a Lipidara driver.
  - **Must not say** "BXC fell 6% nationally" with no mention of Metacora.
  - **Action.** Ace scans the dropped list to confirm nothing large is missing, then signs off the draft for P2.
  - **Eval items** EV-3.1, EV-3.3.
### **BXC-P1-Q6 · How much do I have to rewrite before this goes to my manager?**
*As Ace, I want a draft in our Monday format that needs only wording fixes, so that the agent saves real time.*
  - **Answer from the data (week of 2026-08-24).** The data cannot measure rewriting; review does. What the data fixes is the content: for the week of 2026-08-24, a correct Lipidara draft carries a continuing Metacora line (week 26 since launch: Metacora 15.9% of the basket, Lipidara 30.5%) and nothing about a national "collapse": national BXC TRx was 4,125, 2.5% below its 4-week average. It carries no Southeast coverage story: Lipidara rep calls in Southeast averaged 36 a week in August, against a median of 33.
  - **Given** the 2026-08-24 snapshot. **When** the Lipidara (BXC) draft reaches Ace. **Then** it follows the team template, every figure is a filled claim token, and "new patients" appears only for NBRx.
  - **Must not say** "new patients" for NRx, a Southeast coverage story for Lipidara, or any figure typed outside a claim token.
  - **Action.** Ace edits wording only. Each edit gets a failure tag; a fix repeated in two weeks becomes a new eval case.
  - **Eval items** EV-8.1, EV-7.4, EV-9.2.
## **P2 · Insights Manager (Marcus)**
Marcus signs off the brief and defends it to leadership. His stories test whether the story is real and whether he can stand behind it.
### **BXC-P2-Q1 · Is this change real, or a data or calendar artifact?**
*As Marcus, I want data artifacts separated from business change before any explanation, so that I never send leadership a story that unravels.*
  - **Answer from the data (week of 2026-04-06, today's snapshot).** Summed over reportable cuts, national BXC TRx is 3,892, down 19.4% from 4,826 the week before. But Mid-Atlantic is withheld: its feed for that week is flagged RESTATEMENT_REVIEW. On the 7 territories that report both weeks, BXC went from 4,008 to 3,892, a 2.9% dip.
  - **Given** a week where one territory's cut is withheld for restatement review. **When** the Lipidara (BXC) brief re-runs on the current snapshot. **Then** the national dip is labelled a data artifact, the like-for-like change on 7 territories is stated, and no business story opens unless that like-for-like change clears the materiality thresholds.
  - **Must not say** "BXC fell 19% nationally."
  - **Action.** Marcus approves the "data artifact" label and raises the restatement review with the data vendor. The brief tells him which cut to re-check.
  - **Eval items** EV-2.2, EV-2.1, EV-3.2.
### **BXC-P2-Q2 · What explanations were considered, and why were the others ruled out?**
*As Marcus, I want competing explanations tested and recorded, so that "what about the competitor?" has an answer on the spot.*
  - **Answer from the data (weeks of 2026-05-11 to 2026-06-29).** Competitor, supported. Metacora (BXE) launched on 2026-03-02 and held 11.8% of the four-brand basket in these weeks. Lipidara's share was 31.2%, against 35.4% in the four weeks before launch (2026-02-02 to 2026-02-23), and its TRx averaged 17.7% below those four weeks. Access, ruled out: no Lipidara plan changed tier, prior authorization or step therapy between 2026-02 and 2026-06, and Metacora entered at tier 3, the same tier as Lipidara (3). Promotion, ruled out: Lipidara rep calls across all territories averaged 211 a week against 220 before, and no territory fell below 0.85 of its own pre-launch level. Supply, ruled out: Lipidara inventory fill never fell below 0.956. Data artifact, ruled out: no feed flags in these weeks, every territory passes.
  - **Given** a national share loss with one live competitor launch and stable access, promotion, supply and feeds. **When** the Lipidara (BXC) brief investigates. **Then** the story names the competitor as the leading driver and lists each alternative with its verdict and evidence link.
  - **Must not say** a single cause with no alternatives on record.
  - **Action.** Marcus walks into the brand meeting with the ruled-out list. The brief tells him to involve market access and marketing on the competitive response.
  - **Eval items** EV-4.1, EV-4.2, EV-5.1.
### **BXC-P2-Q3 · How confident are we, and where should we say we don't know yet?**
*As Marcus, I want an honest "not enough evidence yet," so that I never overclaim in front of leadership.*
  - **Answer from the data (weeks of 2026-06-15 to 2026-07-13, South Central).** Like for like (the seven territories that report in every week compared; Great Lakes is out because its 2026-07-06 feed fails), South Central BXC TRx averaged 17.0% below the four weeks before (2026-05-18 to 2026-06-08) while the other territories rose 0.6%, a gap of 17.6 points. Nothing in the context tables explains it: South Central rep calls averaged 27 a week (median 27) with no vacancy, no Lipidara plan changed tier, prior authorization or step therapy, inventory fill averaged 0.987, and every South Central feed passed. Metacora's share there (13.0%) is within the range of the other territories (12.3% to 13.5%).
  - **Given** a sustained regional gap with no driver visible in access, promotion, supply, competitor or feed data. **When** the Lipidara (BXC) brief investigates. **Then** the story closes at Low confidence as "unresolved, investigate next," lists the checks run, and names no driver.
  - **Must not say** "South Central is down because of Metacora."
  - **Action.** Marcus presents it as "still investigating." The brief tells him what to check next: plan and specialty splits, and local context from sales leadership.
  - **Eval items** EV-5.1, EV-5.2, EV-5.3.
### **BXC-P2-Q4 · Where is the change concentrated?**
*As Marcus, I want a national number broken down to where it actually happens, so that the right team acts.*
  - **Answer from the data (weeks of 2025-08-04 to 2025-10-27).** Nationally the rise is broad: like for like, BXC TRx rose 12.4% against June and July (Labor Day week left out). Mid-Atlantic rose 13.9%. Inside Mid-Atlantic, one Medicare Part D plan with 25.0% of the territory's BXC TRx rose 21.1% (about 34 TRx a week), while the territory's other plans rose 11.5%. Among specialties on that plan, internal medicine gained most, 40.0 to 55.4 TRx a week.
  - **Given** a plan-level rise inside a broader national rise. **When** the Lipidara (BXC) brief runs. **Then** concentration names territory, channel, plan and specialty, and the segment contributions sum to the territory change.
  - **Must not say** "Mid-Atlantic Medicare is up" without the plan, or "Mid-Atlantic grew evenly."
  - **Action.** Marcus routes the story to market access with the plan named.
  - **Eval items** EV-4.3, EV-3.1.
### **BXC-P2-Q5 · If someone challenges a claim, can I show the evidence behind it?**
*As Marcus, I want every claim answered against the numbers as they stood at sign-off, so that a challenge does not mean rebuilding the analyst's work.*
  - **Answer from the data (week of 2026-04-06, Mid-Atlantic).** Mid-Atlantic's cut for the week of 2026-04-06 is withheld for restatement review, so national BXC TRx is 3,892 across 7 of 8 territories, with no Mid-Atlantic figure in it. No Lipidara figure was restated: the restatement log holds no row for BXC, and none for Mid-Atlantic that week. The only restatement in the release belongs to another product. A challenge to a Mid-Atlantic Lipidara number for that week is answered with the withheld flag, not with a restated value.
  - **Given** a challenge to a Lipidara figure for a week where the territory's cut was withheld. **When** someone challenges the April number. **Then** its evidence link opens the gated view on the pinned snapshot, shows Mid-Atlantic as withheld, and the restatement record shows no BXC row, so no restated figure is quoted.
  - **Must not say** "Lipidara Mid-Atlantic TRx was restated", or any Mid-Atlantic BXC figure for that week.
  - **Action.** Marcus answers on the spot: the Mid-Atlantic cut was withheld, and nothing was restated for Lipidara.
  - **Eval items** EV-6.2, EV-1.2.
### **BXC-P2-Q6 · Is this freeing my team's time without risking our credibility?**
*As Marcus, I want time saved and errors counted side by side, so that I adopt the agent on evidence.*
  - **Answer from the data.** Time cannot be read from the data; the run measures it. What the data sets is the risk test: the release has three feed artifacts and holiday weeks that drop national BXC TRx against the 4-week average, by 14.3% to 21.1% in the Thanksgiving, Christmas and New Year weeks of 2024 and 2025 and by 8.8% to 18.8% in the feed-artifact weeks. Reading any of them as a business event is a critical error.
  - **Given** a held-out stretch of weeks that includes artifacts and holidays. **When** every version of the Lipidara (BXC) brief runs on it. **Then** the scorecard reports run time, reviewer minutes, cost, critical errors and run-to-run spread for each version against the manual baseline.
  - **Must not say** "saves X hours" without the critical-error rate beside it.
  - **Action.** Marcus decides on adoption from the scorecard.
  - **Eval items** EV-8.2, EV-8.3, EV-8.4, EV-8.5.
## **P3 · Brand Director (Diana)**
Diana reads only the brief P2 approved and carries it to leadership. Her stories test the "so what" and whether she can repeat it safely.
### **BXC-P3-Q1 · What changed this week that I need to know about?**
*As Diana, I want the two or three changes that matter at the top, so that I don't dig through a long report.*
  - **Answer from the data (week of 2026-04-27).** Eight weeks after launch, competitor Metacora (BXE) held 9.3% of the four-brand basket. Lipidara's share was 31.6%, down 3.8 points from 35.4% in the four weeks before launch (2026-02-02 to 2026-02-23). No Lipidara access change (none in the release) and no supply shortfall (fill 0.957 or higher) sits in that week.
  - **Given** a competitor launch eight weeks old and still gaining. **When** the Lipidara (BXC) brief runs. **Then** the first story is Metacora's share gain and Lipidara's share loss, with both figures and the launch date.
  - **Must not say** a list of territory moves with the competitor story buried below them.
  - **Action.** Diana raises competitive response at the leadership meeting. The brief tells her to loop in sales and marketing.
  - **Eval items** EV-3.1, EV-3.3.
### **BXC-P3-Q2 · Does this matter for the brand, or can I ignore it?**
*As Diana, I want expected seasonal dips labelled, so that I am not pulled into false alarms.*
  - **Answer from the data (weeks of 2025-12-22 and 2025-12-29).** National BXC TRx was 4,041 and 3,987, together 20.2% below the four weeks before (2025-11-24 to 2025-12-15), or 19.7% and 20.8% week by week. Both weeks had 4 business days, and the second was the plan-year reset. The same two weeks a year earlier were 18.4% below their four weeks before (2024-11-25 to 2024-12-16), or 21.1% and 15.6% week by week. The next week rebounded to 4,656, up 16.8%.
  - **Given** two holiday weeks with lower business days. **When** the Lipidara (BXC) brief runs. **Then** it labels the drop a calendar effect, cites last year's same weeks, and opens no story.
  - **Must not say** "BXC fell 20%" with no calendar label.
  - **Action.** Diana ignores it. The brief tells her to expect the rebound the next week.
  - **Eval items** EV-3.4, EV-3.2.
### **BXC-P3-Q3 · Why did it happen, in terms I can explain to my leadership?**
*As Diana, I want the explanation in plain words with one number each, so that I can repeat it upward.*
  - **Answer from the data (weeks of 2026-06-01 to 2026-06-29).** A plain-language version: "A new competitor, Metacora, launched on March 2. By June it filled 12.6 of every 100 prescriptions in this market. Lipidara's share fell from 35.4 of every 100 to 31.3. Lipidara's prescriptions are 18.1% below the weeks before the launch. Nothing changed in Lipidara's insurance coverage."
  - **Given** a competitor launch that took share from a brand whose own coverage did not change. **When** the Lipidara (BXC) brief writes the story. **Then** it uses short sentences, one idea and one number per sentence, and calls it a competitor problem, not a coverage or supply problem.
  - **Must not say** "difference-in-differences," "share of voice," or any term Diana would have to translate.
  - **Action.** Diana tells leadership it was a new competitor, not Lipidara's coverage. The brief tells her to ask marketing for its defense plan.
  - **Eval items** EV-7.1.
### **BXC-P3-Q4 · Is this new or the same issue as last week, and is it getting better or worse?**
*As Diana, I want continuing stories marked with their trend, so that repeated alarms don't erode attention.*
  - **Answer from the data (week of 2026-09-28).** The Metacora story is in its 31st week. Its share of the basket, averaged over 4-week blocks, went 2.2%, 6.7%, 9.8%, 12.0%, 13.1%, 13.8%, 15.3% and 15.2%. Lipidara's share over the same blocks went 34.7%, 33.2%, 31.5%, 31.1%, 30.4%, 30.9%, 29.8% and 29.7%. It is worse than at launch but has flattened for the last 8 weeks. That week Lipidara held 29.4% and Metacora 15.2%.
  - **Given** a story that has run for months. **When** the Lipidara (BXC) brief runs. **Then** it is marked "continuing," states the direction (worse, now flat), and is not rediscovered as new.
  - **Must not say** "New: competitor gaining share."
  - **Action.** Diana moves from alarm to monitoring. The brief tells her to ask marketing for its defense plan.
  - **Eval items** EV-7.2.
### **BXC-P3-Q5 · What should I do, and who should I loop in?**
*As Diana, I want next steps and the right function named, so that implications for sales, access and finance are not left implicit.*
  - **Answer from the data (weeks of 2025-08-04 to 2025-10-27, Mid-Atlantic).** Lipidara TRx on one Mid-Atlantic Medicare Part D plan rose 21.1% (162 to 197 TRx a week, Labor Day week left out) without any change on Lipidara's side there: rep calls in Mid-Atlantic averaged 32 a week against 31 before, and Lipidara's tier on the plan stayed at 3. The change on the plan was a competitor's: Cardiovela (BXA) moved from tier 2 to tier 3 on 2025-08-01 and returned to tier 2 on 2025-11-01. The plan carries 26.0% of the territory's covered lives. Next steps: involve market access on that plan (what Lipidara's own formulary position is, and whether the competitor's move will repeat) and sales leadership on Mid-Atlantic, at territory level.
  - **Given** a plan-level rise that came from a competitor's access change, shown only at plan and territory level. **When** the Lipidara (BXC) brief writes next steps. **Then** it says "involve market access on the plan" and "involve sales leadership on Mid-Atlantic," and stays at territory level.
  - **Must not say** any line that points to one rep, or a claim that Lipidara's own access improved.
  - **Action.** Diana asks market access about the plan and takes the finding into budget talks with P4.
  - **Eval items** EV-7.3, EV-9.1.
### **BXC-P3-Q6 · Can I quote these numbers in my leadership meeting?**
*As Diana, I want numbers that will not be corrected later, so that my credibility holds upward.*
  - **Answer from the data (brief of 2026-07-13).** No Lipidara figure has been restated: the restatement log holds no row for BXC. Projected national BXC TRx for the week of 2026-07-13 is 3,830, with every territory observed (8 of 8 pass). The like-for-like change against the four weeks before (2026-06-15 to 2026-07-06) is 6.1% down and covers 7 of 8 territories, because Great Lakes failed its checks for 2026-07-06. Three weeks in the release have one failed territory cut (2026-04-06, 2026-05-04, 2026-07-06); their projected national labels that territory as projected or estimated, an assumption, instead of leaving it out.
  - **Given** a brief for a week after a failed feed, with no restatement of any Lipidara number. **When** the next Lipidara (BXC) brief runs. **Then** it quotes the KPI table without a correction note, any like-for-like figure built on 7 territories says so, and the projected national labels a projected or estimated territory as an assumption instead of leaving it out.
  - **Must not say** a restatement note for a Lipidara number that was not restated, or a like-for-like change that does not say it covers 7 of 8 territories.
  - **Action.** Diana quotes only from the KPI table. The brief tells her no earlier Lipidara figure changed.
  - **Eval items** EV-1.1, EV-1.2.
## **P4 · Marketer (Magdalena)**
Magdalena runs promotion with the budget P3 sets and reads the brief after P2 signs off. Her stories test promotion as one driver among several, never assumed.
### **BXC-P4-Q1 · Did my campaign move brand sales, and by how much?**
*As Magdalena, I want promotion tested with a verdict either way, so that sales gains are not credited to whichever campaign launched last.*
  - **Answer from the data (week of 2026-08-10, Southeast).** The release has no lasting Lipidara campaign push: in no territory did rep calls stay above 1.25 times their median for more than 3 weeks in a row. The clearest spike is Southeast in the week of 2026-08-10: rep calls were 49 against a median of 33, and digital impressions 1,125 against a median of 1,122.5. Southeast BXC TRx that week was 583, 9.3% below its previous four weeks (2026-07-13 to 2026-08-03, average 643) while the other territories rose 5.3%. The next week it was 649, 0.9% above those four weeks. Promotion is not supported: the spike week did not lift TRx.
  - **Given** a territory where one week of promotion activity stands out from its median. **When** the Lipidara (BXC) brief tests promotion. **Then** promotion gets a verdict of not supported for that week, with the TRx before, during and after stated and no lift credited to the campaign.
  - **Must not say** "promotion caused a lift," or credit promotion in any week where its activity did not change.
  - **Action.** Magdalena does not use the spike week as evidence of a campaign effect.
  - **Eval items** EV-4.5, EV-4.1.
### **BXC-P4-Q2 · Which geographies, segments and channels responded, and which did not?**
*As Magdalena, I want the effect broken down by geography and channel, so that I can compare a campaign's area with the rest.*
  - **Answer from the data (weeks of 2026-09-14 to 2026-10-05).** Over the latest four weeks (2026-09-14 to 2026-10-05), Lipidara TRx was 9.8% below the four weeks before Metacora launched (2026-02-02 to 2026-02-23), like for like on all 8 territories. The change is broad, not local. By territory: Mountain up 2.0%, Pacific down 4.9%, Northwest down 9.1%, Great Lakes down 9.3%, New England down 11.3%, Southeast down 11.7%, Mid-Atlantic down 13.7% and South Central down 15.4%. By channel: Medicaid down 6.0%, commercial down 10.4%, Medicare Part D down 10.7% and cash down 11.7%. By specialty: endocrinology down 7.1%, cardiology down 8.8%, primary care down 10.0% and internal medicine down 11.4%. Cash is a small cell (265 TRx a week nationally, as few as 18 a week in the smallest territory), so its figure is noisy.
  - **Given** a brand-wide share loss with no territory lapse in promotion. **When** the Lipidara (BXC) brief reports it. **Then** it shows each territory, channel and specialty against the pre-launch weeks, says the loss is broad, and flags small cells (cash) as noisy.
  - **Must not say** "cash patients are leaving Lipidara fastest" from a base of a few dozen prescriptions a week.
  - **Action.** Magdalena notes that the loss is broad, so she plans by brand, not by territory or channel.
  - **Eval items** EV-4.3, EV-7.5.
### **BXC-P4-Q3 · Did the campaign reach the people it was meant to reach?**
*As Magdalena, I want reach shown next to results, so that high impressions cannot hide low engagement.*
  - **Answer from the data (weeks of 2025-08-04 to 2025-10-27, Mid-Atlantic).** Partly. The data has digital impressions and rep calls by territory, product and week: in Mid-Atlantic in these weeks (Labor Day week left out), Lipidara impressions averaged 1,076 against a median of 1,138.5 and rep calls 32 against 33, so activity was steady while TRx rose 13.9%. It has no reach by target segment, no channel spend and no consumer campaigns.
  - **Given** promotion data at territory level only. **When** the Lipidara (BXC) brief shows a promotion story. **Then** it puts calls and impressions beside TRx for the same cut and weeks, and says that reach in the target segment cannot be shown yet.
  - **Must not say** "the campaign reached its target HCPs."
  - **Action.** Magdalena asks for channel spend and reach data. The brief tells her this is open (Architecture A16).
  - **Eval items** EV-7.5.
### **BXC-P4-Q4 · Is the lift real, or was it access, a competitor or the season?**
*As Magdalena, I want lifts tested against access, competitors and season, so that I never claim credit for a formulary win.*
  - **Answer from the data (weeks of 2025-11-03 to 2025-12-15, Mid-Atlantic).** Lipidara on the Mid-Atlantic Medicare Part D plan rose 37.2% (162 to 223 TRx a week, Thanksgiving week left out) against the summer (2025-06-02 to 2025-07-28). Part of the lift is seasonal: national BXC TRx rose 19.3% over the same weeks and the territory's other plans 20.9%. The plan rose 16.3 points more than those other plans, and no driver in the data explains that. It is not promotion: Mid-Atlantic rep calls averaged 30 a week against 31 in the summer. It is not Lipidara's access: its tier on the plan stayed at 3. Nor is it the competitor's move: Cardiovela's tier on the plan went back to 2 on 2025-11-01, which would pull Lipidara down, not up.
  - **Given** a lift on one plan that is bigger than the season explains, with steady promotion and unchanged access. **When** the Lipidara (BXC) brief tests promotion. **Then** promotion is "ruled out," access is ruled out, the seasonal share is noted, and the rest is left unexplained rather than credited.
  - **Must not say** "Q4 promotion lifted Mid-Atlantic."
  - **Action.** Magdalena leaves this lift out of her campaign review.
  - **Eval items** EV-4.5, EV-4.2, EV-3.4.
### **BXC-P4-Q5 · How confident is the estimate, and when will we know more?**
*As Magdalena, I want confidence and timing stated plainly, so that early reads don't mislead the budget.*
  - **Answer from the data (weeks of 2025-08-04 to 2025-10-27, Mid-Atlantic).** Low. The Mid-Atlantic estimate rests on one plan in one territory and is an association. From 2025-08-04 to 2025-10-27 (Labor Day week left out), Lipidara TRx on the plan rose 21.1% against the summer, 9.6 points more than the territory's other plans (11.5%). At most, that gap is what a competitor's tier change on 2025-08-01 could account for. The one test the data offers did not confirm it: when Cardiovela's tier went back to 2 on 2025-11-01, Lipidara's plan TRx kept rising (13.3% above August to October, against 8.4% for the other plans). In this data a formulary change shows within the first week, so a re-read four weeks after the plan's next change is enough.
  - **Given** one plan in one territory, one competitor access change and one reversal. **When** the Lipidara (BXC) brief reports confidence. **Then** it says Low, names the single plan, says the figure is an association, and states when the next read is due.
  - **Must not say** "High confidence" from one plan.
  - **Action.** Magdalena waits for the four-week re-read before moving budget.
  - **Eval items** EV-5.1, EV-4.4, EV-7.2.
### **BXC-P4-Q6 · Where should the next dollar go?**
*As Magdalena, I want budget arguments grounded in evidence, so that shifts are not argued from anecdote.*
  - **Answer from the data (weeks of 2026-09-14 to 2026-10-05).** The data supports no territory-specific shift for Lipidara. No territory had a promotion lapse: rep calls across all territories averaged 215 a week against 220 before Metacora launched, and no territory fell below 0.91 of its own pre-launch level. Digital impressions across all territories were 7,613 a week against 7,295. TRx is 9.8% below the pre-launch weeks and the loss is broad: 7 of 8 territories are below their own pre-launch level, South Central most (15.4%) and Mountain not at all (up 2.0%). It cannot rank channels or price a dollar: there is no spend data, no reach by segment, and no promotion change to measure a response against.
  - **Given** a brand-wide share loss with steady promotion in every territory. **When** the Lipidara (BXC) brief writes next steps. **Then** it says the data supports no territory-specific shift, recommends discussing next steps with marketing at brand level, and says the promotion effect cannot be measured here.
  - **Must not say** a cost per incremental prescription, or any rep-level line.
  - **Action.** Magdalena takes the finding into the budget talk with P3 and asks for spend and reach data to test a response.
  - **Eval items** EV-7.3, EV-9.1.
# **Coverage and gaps**
## **Coverage: question to anchor, eval items and stage**
| Question | Anchor | Eval items | Stage |
| :- | :- | :- | :- |
| BXC-P1-Q1 | Great Lakes duplicates, 2026-07-06 (Lipidara) | EV-1.1, EV-2.1, EV-2.3 | 2, 6 |
| BXC-P1-Q2 | New England incomplete feed, 2026-05-04 (Lipidara) | EV-2.1, EV-2.3, EV-1.1 | 2 |
| BXC-P1-Q3 | Quiet week, 2025-04-14 (Lipidara) | EV-3.2, EV-3.3 | 3a |
| BXC-P1-Q4 | Mid-Atlantic plan, competitor access change, Aug to Oct 2025 (Lipidara) | EV-6.1, EV-6.2, EV-6.3 | 6, 7 |
| BXC-P1-Q5 | Metacora, with Pacific checked, 2026-06-08 (Lipidara) | EV-3.1, EV-3.3 | 3a, 4a |
| BXC-P1-Q6 | Draft for 2026-08-24 (Lipidara) | EV-8.1, EV-7.4, EV-9.2 | 5, 7 |
| BXC-P2-Q1 | Mid-Atlantic cut withheld, 2026-04-06 (Lipidara) | EV-2.2, EV-2.1, EV-3.2 | 2, 4a |
| BXC-P2-Q2 | Metacora era, competing explanations (Lipidara) | EV-4.1, EV-4.2, EV-5.1 | 4a |
| BXC-P2-Q3 | South Central gap, Jun to Jul 2026 (Lipidara) | EV-5.1, EV-5.2, EV-5.3 | 4a, 6 |
| BXC-P2-Q4 | Mid-Atlantic plan, Aug to Oct 2025 (Lipidara) | EV-4.3, EV-3.1 | 4a |
| BXC-P2-Q5 | Mid-Atlantic withheld, no Lipidara restatement (Lipidara) | EV-6.2, EV-1.2 | 1, 6 |
| BXC-P2-Q6 | Held-out stretch with artifacts and holidays (Lipidara) | EV-8.2, EV-8.3, EV-8.4, EV-8.5 | Cross-cutting |
| BXC-P3-Q1 | Metacora at 8 weeks, 2026-04-27 (Lipidara) | EV-3.1, EV-3.3 | 3a |
| BXC-P3-Q2 | Holiday weeks, Dec 2025 (Lipidara) | EV-3.4, EV-3.2 | 3a |
| BXC-P3-Q3 | Metacora share gain in plain words, Jun 2026 (Lipidara) | EV-7.1 | 5 |
| BXC-P3-Q4 | Metacora at 31 weeks, 2026-09-28 (Lipidara) | EV-7.2 | 4a, 5 |
| BXC-P3-Q5 | Mid-Atlantic plan, competitor access change, Aug to Oct 2025 (Lipidara) | EV-7.3, EV-9.1 | 5, 6 |
| BXC-P3-Q6 | No Lipidara restatement, brief of 2026-07-13 (Lipidara) | EV-1.1, EV-1.2 | 2, 5, 6 |
| BXC-P4-Q1 | Southeast rep-call spike, 2026-08-10 (Lipidara) | EV-4.5, EV-4.1 | 4a |
| BXC-P4-Q2 | Metacora era split by territory, channel, specialty (Lipidara) | EV-4.3, EV-7.5 | 4a, 5 |
| BXC-P4-Q3 | Impressions without reach data, Mid-Atlantic Aug to Oct 2025 (Lipidara) | EV-7.5 | 5 |
| BXC-P4-Q4 | Mid-Atlantic plan lift, Nov to Dec 2025 (Lipidara) | EV-4.5, EV-4.2, EV-3.4 | 4a |
| BXC-P4-Q5 | Confidence in the Mid-Atlantic plan estimate (Lipidara) | EV-5.1, EV-4.4, EV-7.2 | 4a |
| BXC-P4-Q6 | No territory lapse, broad Metacora-era loss (Lipidara) | EV-7.3, EV-9.1 | 5, 6 |
