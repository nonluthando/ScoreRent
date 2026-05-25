from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class EvaluationResult:
    """
    Final evaluation output.

    Stores:

    - score
    - recommendation verdict
    - confidence level
    - reasons
    - actions
    - explainability breakdown
    """

    score: int

    verdict: str

    confidence: str

    reasons: List[str]

    actions: List[str]

    breakdown: List[
        Dict[str, Any]
    ]
