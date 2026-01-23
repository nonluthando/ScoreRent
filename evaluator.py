def evaluate(renter, listing):
    score = 100
    reasons = []

    # Rent vs income
    if listing.rent / renter.monthly_income > 0.35:
        score -= 30
        reasons.append("Rent exceeds recommended affordability threshold")

    # Budget
    if listing.rent > renter.budget:
        score -= 20
        reasons.append("Rent exceeds stated budget")

    # Deposit
    if listing.deposit > renter.budget:
        score -= 10
        reasons.append("Deposit may be difficult to afford")

    # Documents
    renter_docs = set(renter.documents)
    required_docs = set(listing.required_documents)
    missing = required_docs - renter_docs

    if not missing:
        score += 10
        reasons.append("All required documents are available")
    elif len(missing) == 1:
        score -= 10
        reasons.append(f"Missing required document: {missing.pop()}")
    else:
        score -= 30
        reasons.append("Multiple required documents are missing")

    # Area demand
    if listing.area_demand == "HIGH":
        score -= 10
        reasons.append("High demand area increases competition")

    # Application fee (risk)
    if listing.application_fee > 0:
        fee_ratio = listing.application_fee / renter.budget
        if fee_ratio > 0.05:
            score -= 15
            reasons.append("High application fee relative to budget")
        if score < 60:
            score -= 10
            reasons.append(
                "Application fee increases cost of a low-confidence application"
            )

    score = max(0, min(score, 100))

    if score >= 70:
        verdict = "WORTH_APPLYING"
    elif score >= 40:
        verdict = "BORDERLINE"
    else:
        verdict = "NOT_WORTH_IT"

    return score, verdict, reasons
