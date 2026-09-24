> Reference copy of the build guide, exported 24 Sep 2026. The living doc is the source of truth and tracks progress: https://claude.ai/code/artifact/f66041c7-114a-4c2e-be32-f922f5293e7e
> Checkbox state here means nothing; ask Rehan which step he's on.

## Week 8: Prove it, package it, ship it

By Sunday, the repo is public with a README, a results table and a demo video, and your resume bullets carry real numbers. Whatever time is left is buffer for anything that slipped.

**Files this week.** All new, whole files.

| File | What you do | Step |
| --- | --- | --- |
| `evals/recall.py` | Create | Measure it |
| `evals/labels.json` | Add moments for 7 more videos | Measure it |
| `scripts/cost_per_clip.py` | Create: the cost script | Measure it |
| `docs/results.md` | Create | Measure it |
| `README.md` | Create, in `clip-agent/` | Package it |

### Measure it (about 5 hours)

- [ ] Run the Moment Finder on the 3 videos you labelled in week 1, plus 7 more you label now, and score each with `evals/recall.py`:

```python
"""Recall@k: how many of your hand-picked best moments the Moment Finder also found.

Usage: python evals/recall.py RUN_ID ep12.mp4 [k]
labels.json looks like {"ep12.mp4": [{"start": 312, "end": 345}, ...]}
"""
import json
import sys

import boto3
from boto3.dynamodb.conditions import Key

TABLE = "ClipStorage-StateXXXX"  # your table name


def overlap(a, b):
    """Seconds shared by two (start, end) spans."""
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def found(label, candidates, min_share=0.5):
    """A label counts as found if one candidate covers at least half of it."""
    length = label[1] - label[0]
    return any(overlap(label, c) >= min_share * length for c in candidates)


def recall_at_k(labels, candidates, k=10):
    top = candidates[:k]
    hits = sum(found(label, top) for label in labels)
    return hits / len(labels) if labels else 0.0


if __name__ == "__main__":
    run_id, video, k = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10
    labels = [(m["start"], m["end"]) for m in json.load(open("evals/labels.json"))[video]]
    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE)
    items = table.query(KeyConditionExpression=Key("pk").eq(f"VIDEO#{run_id}") & Key("sk").begins_with("CAND#"))["Items"]
    candidates = [(c["start"], c["end"]) for c in (json.loads(i["data"]) for i in sorted(items, key=lambda i: i["sk"]))]
    print(f"recall@{k} = {recall_at_k(labels, candidates, k):.0%} ({len(labels)} labelled moments)")
```

- [ ] Put the same 10 videos through Crayo's AutoClip, note its picks' start and end times, and score them with the same `recall_at_k`. That gives you "my agent vs a commercial tool".
- [ ] Plant problems in 10 real clips (a cut that flips the speaker's meaning, a missing hashtag, a clip that's too long) next to 10 clean ones. Count how many the Compliance Reviewer catches, and how many clean clips it wrongly flags.
- [ ] Activate the `project` cost allocation tag in Billing (it takes up to a day to appear), then run the cost script at month end:

```python
"""This month's AWS bill divided by approved clips. Run it at the end of each month."""
import datetime

import boto3
from boto3.dynamodb.conditions import Attr

TABLE = "ClipStorage-StateXXXX"  # your table name

today = datetime.date.today()
start = today.replace(day=1)
ce = boto3.client("ce", region_name="us-east-1")  # each Cost Explorer API call costs $0.01
cost = ce.get_cost_and_usage(
    TimePeriod={"Start": start.isoformat(), "End": today.isoformat()},
    Granularity="MONTHLY",
    Metrics=["UnblendedCost"],
)["ResultsByTime"][0]["Total"]["UnblendedCost"]
table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE)
approved = table.scan(
    FilterExpression=Attr("status").eq("APPROVED"), Select="COUNT"
)["Count"]  # all-time count; filter by date once you have months of data

total = float(cost["Amount"])
print(f"AWS so far this month: ${total:.2f}")
print(f"Approved clips (all time): {approved}")
if approved:
    print(f"Cost per approved clip: ${total / approved:.2f} (plus Upload-Post and Crayo subscriptions)")
```

- [ ] Fill in `docs/results.md`:

| Measure | Manual (week 1) | System (week 8) |
| --- | --- | --- |
| Your minutes per published clip | from your spreadsheet | from Telegram timestamps |
| Moment recall@10 | Crayo AutoClip's score | Moment Finder's score |
| Candidate approval rate | not applicable | approved ÷ sent |
| Compliance catch rate | not applicable | planted problems caught |
| Cost per approved clip | Crayo plan ÷ clips | cost script |
| Verified views and earnings | week 1 total | weeks 5–8 total |

### Package it (about 6 hours)

- [ ] Write the README: the problem, the architecture diagram, how a clip flows, three decision records (Step Functions orchestrating agents, human approval as a feature, building versus buying rendering), the results table, security, costs, and what you'd build next.
- [ ] Scan the repo's history for secrets before going public (GitHub's secret scanning or `gitleaks`), then make it public and tag `v2.0`.
- [ ] Record a 2-minute demo: upload, previews on your phone, approve, the post goes live, the submit link, the weekly report, and the denied `publish_now` call.
- [ ] Publish a write-up on AWS Builder Center or dev.to, such as "A human-approved agent pipeline on AWS".
- [ ] Swap real numbers into the resume bullets from the architecture doc, and post the demo on LinkedIn.

### Buffer

- [ ] Finish anything that slipped from weeks 5–7, MVP first.
- [ ] Fix the top three issues from your latest weekly report.
- [ ] Pick one item from your "Later" list for after exams, and stop there.

When you pause the project, disable the two EventBridge schedules (`aws events disable-rule --name ...`). With nothing uploaded, the rest costs almost nothing, because every piece is pay-per-use.

**Done when:** the repo is public with its README, results and demo, the write-up is live, and your resume shows the numbers.
