from config import (
    CAPE_TOWN_RECOMMENDED_CAP,
    CAPE_TOWN_UPPER_CAP,
    CAPE_TOWN_EXTREME_CAP,
)


def calculate_budget_guidance(
    income: float | None,
):

    income = income or 0

    recommended = round(
        income *
        CAPE_TOWN_RECOMMENDED_CAP
    )

    stretch = round(
        income *
        CAPE_TOWN_UPPER_CAP
    )

    high_risk = round(
        income *
        CAPE_TOWN_EXTREME_CAP
    )

    return {

        "recommended": recommended,

        "stretch": stretch,

        "high_risk": high_risk,

    }
