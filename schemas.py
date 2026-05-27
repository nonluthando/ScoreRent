from pydantic import BaseModel
from typing import List, Literal


# -------------------------
# Inputs
# -------------------------

class RenterProfile(BaseModel):
    monthly_income: int
    budget: int
    documents: List[str]


class Listing(BaseModel):
    rent: int
    deposit: int
    application_fee: int
    required_documents: List[str]
    area_demand: Literal["LOW", "MEDIUM", "HIGH"]


class EvaluationRequest(BaseModel):
    renter: RenterProfile
    listing: Listing


# -------------------------
# Outputs
# -------------------------

class BudgetSuggestion(BaseModel):
    conservative: int
    recommended: int
    upper_limit: int


class EvaluationResponse(BaseModel):
    score: int
    verdict: Literal["WORTH_APPLYING", "BORDERLINE", "NOT_WORTH_IT"]
    reasons: List[str]
    suggested_budget: BudgetSuggestion
