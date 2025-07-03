import pandas as pd
import re
from datetime import datetime, timedelta

df = pd.read_csv("tenders/claude_extracted.csv")

preferred_locations = ["Bishkek", "Osh", "Chuy"]
domain_keywords = ["road", "construction", "repair", "renovation", "design", "school"]
min_budget = 1_000_000  # in KGS
max_budget = 10_000_000
min_days_until_deadline = 5
risk_keywords = ["penalty", "lawsuit", "urgent", "tight deadline", "delay", "high complexity"]

def parse_budget(budget_str):
    try:
        nums = re.findall(r"[\d,]+", budget_str.replace(" ", ""))
        if nums:
            clean = nums[0].replace(",", "")
            return int(clean)
    except:
        return None
    return None

def parse_deadline(deadline_str):
    try:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(deadline_str.strip(), fmt)
            except:
                continue
    except:
        return None
    return None

def score_row(row):
    sector_score = 10 if any(k in str(row["project_type"]).lower() for k in domain_keywords) else 0

    budget_val = parse_budget(str(row["budget"]))
    if budget_val:
        if min_budget <= budget_val <= max_budget:
            budget_score = 10
        elif budget_val < min_budget:
            budget_score = 5
        else:
            budget_score = 7
    else:
        budget_score = 0

    location_score = 10 if any(loc.lower() in str(row["location"]).lower() for loc in preferred_locations) else 5

    deadline_dt = parse_deadline(str(row["deadline"]))
    if deadline_dt:
        days_left = (deadline_dt - datetime.today()).days
        if days_left > min_days_until_deadline:
            deadline_score = 10
        elif 0 <= days_left <= min_days_until_deadline:
            deadline_score = 3
        else:
            deadline_score = 0
    else:
        deadline_score = 0

    risk_text = " ".join([str(row.get("title", "")), str(row.get("project_type", ""))])
    risk_hits = sum(1 for kw in risk_keywords if kw in risk_text.lower())
    risk_score = max(0, 10 - risk_hits * 2)

    total = sector_score + budget_score + location_score + deadline_score + risk_score
    return pd.Series({
        "sector_score": sector_score,
        "budget_score": budget_score,
        "location_score": location_score,
        "deadline_score": deadline_score,
        "risk_score": risk_score,
        "total_score": total
    })

score_df = df.apply(score_row, axis=1)
result = pd.concat([df, score_df], axis=1)

result.to_csv("tenders/tender_scores.csv", index=False)
print("✅ Saved scores to tenders/tender_scores.csv")
