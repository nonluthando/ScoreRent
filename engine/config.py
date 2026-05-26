APP_MARKET = "Cape Town"

CURRENCY_CODE = "ZAR"
CURRENCY_SYMBOL = "R"


# --------------------------------------------------
# Affordability thresholds
# --------------------------------------------------

CAPE_TOWN_RECOMMENDED_CAP = 0.33

CAPE_TOWN_UPPER_CAP = 0.38

CAPE_TOWN_EXTREME_CAP = 0.45


# --------------------------------------------------
# Renter types
# --------------------------------------------------

RENTER_TYPES = [
    "worker",
    "new_professional",
    "student",
]


# Optional labels for UI

RENTER_LABELS = {
    "worker": "Worker",
    "new_professional": "New Professional",
    "student": "Student",
}


# --------------------------------------------------
# Demand
# --------------------------------------------------

DEMAND_LEVELS = [
    "LOW",
    "MEDIUM",
    "HIGH",
]


# --------------------------------------------------
# Required documents
# --------------------------------------------------

DOC_CLUSTERS = {

    "worker": [
        "bank statement",
        "payslip",
        "employment letter",
    ],

    "new_professional": [
        "employment contract",
        "offer letter",
        "bank statement",
        "guarantor letter",
    ],

    "student": [
        "bursary award letter",
        "nsfas award letter",
        "bursary confirmation",
        "proof of registration",
        "student ID",
        "guarantor letter",
    ],
}


# --------------------------------------------------
# UI visibility
# controls what appears in forms
# --------------------------------------------------

PROFILE_FIELDS = {

    "worker": [
        "monthly_income",
        "documents",
    ],

    "new_professional": [
        "monthly_income",
        "offer_letter",
        "documents",
        "guarantor",
    ],

    "student": [
        "bursary",
        "nsfas",
        "guarantor",
        "documents",
    ],
}


# --------------------------------------------------
# Evaluation pathways
# --------------------------------------------------

STUDENT_PATHWAYS = {

    "bursary": [
        "bursary award letter",
        "proof of registration",
    ],

    "nsfas": [
        "nsfas award letter",
        "proof of registration",
    ],

    "guarantor": [
        "guarantor letter",
    ],
}


NEW_PROFESSIONAL_PATHWAYS = {

    "contract_route": [
        "employment contract",
    ],

    "offer_route": [
        "offer letter",
    ],

    "guarantor_route": [
        "guarantor letter",
    ],
}
