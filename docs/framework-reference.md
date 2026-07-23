# Framework reference

Reference material gathered while scoping this project, copied here rather than linked
out, so it stays available even if the source pages move. Two sources: the DX AI
Measurement Framework, and the Larridin Developer AI Impact Framework.

## DX AI Measurement Framework

Tracks three dimensions of AI-assisted engineering: utilization (how much AI tooling is
actually being used), impact (how AI affects developer time savings, code quality, and
delivery metrics), and cost (whether AI spend generates a positive return).

**Utilization metrics:**

| Metric | Definition |
|---|---|
| Daily active users (DAU) | Developers using AI at least once per day |
| Weekly active users (WAU) | Developers using AI at least once per week |
| Monthly active users (MAU) | Developers using AI at least once per month |

**Benchmarks and findings:**

- A healthy AI coding tool adoption rate is above 50% WAU within 90 days of deployment,
  with a target of 60-70% WAU at maturity.
- Industry average WAU currently sits at 30-40%.
- Leading engineering organizations achieve 60-70% WAU, with 25-35% of developers
  qualifying as power users (daily usage across multiple AI tool modes).
- Google's 2025 DORA report found that 90% of developers now use AI tools at work.
  Leading organizations are only reaching around 60% active usage of AI tools.
- Daily users ship 60% more PRs than non-users, demonstrating that usage frequency
  strongly correlates with productivity gains.
- AI coding assistants boost individual output — 21% more tasks completed, 98% more
  pull requests merged — but organizational delivery metrics stay flat.
- Code churn roughly doubled from a baseline of approximately 3.3% to between 5.7% and
  7.1% as AI coding tools gained widespread adoption.

## Larridin Developer AI Impact Framework

### Pillar 1: AI Adoption

| Metric | Definition | Calculation |
|---|---|---|
| AI Active User Rate (WAU/DAU/MAU) | Percentage of developers who actively use AI coding tools on a daily, weekly, or monthly basis | Active users / total developers |
| Tool Adoption by Type | Usage segmented across inline completions, chat-based assistance, and agentic workflows | Telemetry from tool dashboards |
| Adoption Distribution | Split between power users (daily, multi-mode), casual users (weekly, single-mode), and non-users | User behavior classification |

Industry benchmarks: 30-40% WAU average; 60-70% top quartile.

### Pillar 2: AI Code Share

| Metric | Definition |
|---|---|
| AI-Assisted PRs % | Percentage of pull requests containing at least one AI-generated or AI-assisted code segment |
| AI-Assisted Lines % | Proportion of committed lines originating from AI suggestions or generations |
| AI-Assisted Commits % | Commits including AI-generated content, measured via tool telemetry |

Industry benchmarks: 20-35% PRs average; 50-70% in high-adoption organizations.

### Pillar 3: Velocity (Complexity-Adjusted Throughput)

| Metric | Definition | Point scale |
|---|---|---|
| Complexity-Adjusted Throughput (CAT) | Engineering output weighted by work difficulty | Easy: 1pt; Medium: 3pts; Hard: 8pts |
| CAT per Engineer (weekly) | Sum of complexity-weighted points delivered per engineer per week | Aggregate merged PR points |
| Delivery Volume (AI vs Human) | Total CAT points broken down by AI-assisted and human-only work | Segmented analysis |
| Cycle Time | Duration from first commit to production deployment | Tracked separately for AI-assisted vs human PRs |

Industry benchmarks: 8 pts/week average; 14+ pts top quartile.

### Pillar 4: Quality

| Metric | Definition |
|---|---|
| Code Turnover Rate (30-day and 90-day) | Percentage of committed code that is substantially rewritten or deleted within 30 or 90 days of being merged |
| AI Code Turnover vs Human Code Turnover | Comparative durability between AI-generated and human-written code |
| Innovation Rate | Percentage of PRs/commits shipping new features versus bug fixes versus infrastructure work |

Industry benchmarks:

- Overall code turnover: 5.7-7.1% (versus a 3.3% pre-AI baseline)
- AI code turnover: 12-18%; human: 4-6%
- AI-to-human ratio: 1.8-2.5x (healthy target: under 1.5x)
- Innovation rate: 45-55% (target: above 50%)

### Pillar 5: Cost and ROI

| Metric | Definition | Formula |
|---|---|---|
| Total AI Tool Cost per Engineer | Fully-loaded cost including seat licenses, token/usage costs, and implementation overhead | Sum of all costs per engineer per month |
| Time Saved Value | Hours saved weighted by loaded engineering cost | Hours saved times ($salary + benefits + overhead) per hour |
| Net ROI Multiplier | (Productive Value of Time Saved minus Rework Cost from Code Turnover) / Total AI Tool Cost | Complete ROI calculation |

Industry benchmarks: 2.5-3.5x ROI average; 4-6x top quartile (red flag: under 2x after
90 days).

### Qualitative layer: developer experience surveys

| Dimension | Measurement | Cadence |
|---|---|---|
| Perceived Time Savings | Developer-reported hours saved per week | Biweekly pulse |
| Post-Acceptance Edit Rate | How often AI output requires substantial revision | Monthly check-in |
| Task Fit | Which work types benefit most from AI assistance | Monthly check-in |
| Adoption Barriers | Obstacles preventing deeper AI tool usage | Quarterly diagnostic |
| AI Tool NPS | Net Promoter Score for AI tool recommendation (0-10) | Biweekly pulse |

### Composite executive metric

The AI Value Realization Score combines all five pillars: WAU Rate (20%), AI-Assisted
Code Rate (20%), Perceived Time Savings Index (30%), Quality Score (30%).

Interpretation: 80-100 excellent; 60-79 good; 40-59 fair; under 40 underperforming.
