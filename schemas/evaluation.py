from typing import List, Literal

from pydantic import BaseModel


# ---------------------------------------------------------
# Input Models
# ---------------------------------------------------------

class RenterProfile(BaseModel):
    renter_type: Literal[
        "worker",
        "new_professional",
        "student",
    ]

    monthly_income: int

    documents: List[str]

    guarantor_monthly_income: int = 0

    is_bursary_student: bool = False


class Listing(BaseModel):
    listing_name: str = ""

    rent: int

    deposit: int

    application_fee: int

    required_documents: List[str]

    area_demand: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
    ]


class EvaluationRequest(BaseModel):
    renter: RenterProfile
    listing: Listing


# ---------------------------------------------------------
# Output Models
# ---------------------------------------------------------

class BudgetSuggestion(BaseModel):
    conservative: int
    recommended: int
    upper_limit: int


class ScoreBreakdownItem(BaseModel):
    title: str
    delta: int
    before: int
    after: int
    details: str


class EvaluationResponse(BaseModel):
    score: int

    verdict: Literal[
        "STRONG_MATCH",
        "BORDERLINE",
        "HIGH_RISK",
    ]

    confidence: Literal[
        "HIGH",
        "MEDIUM",
        "LOW",
    ]

    reasons: List[str]

    actions: List[str]

    breakdown: List[ScoreBreakdownItem]

    suggested_budget: BudgetSuggestion
