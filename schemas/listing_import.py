from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractedField:
    value: Optional[object] = None
    evidence: Optional[str] = None
    confidence: str = "low"


@dataclass
class ListingExtraction:
    listing_name: ExtractedField = field(default_factory=ExtractedField)
    location: ExtractedField = field(default_factory=ExtractedField)
    rent: ExtractedField = field(default_factory=ExtractedField)
    deposit: ExtractedField = field(default_factory=ExtractedField)
    application_fee: ExtractedField = field(default_factory=ExtractedField)
    required_documents: list[str] = field(default_factory=list)
    amenities: list[str] = field(default_factory=list)
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_text: str = ""
