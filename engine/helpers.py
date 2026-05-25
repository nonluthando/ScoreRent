from typing import Any, List


def money(
    value: Any,
) -> int:
    """
    Normalize monetary inputs.

    Invalid values become zero.
    """

    try:

        return max(
            0,
            int(
                round(
                    float(value)
                )
            ),
        )

    except Exception:

        return 0


def ratio_pct(
    numerator: int,
    denominator: int,
) -> float:
    """
    Percentage ratio helper.
    """

    if denominator <= 0:

        return 999.0

    return (
        numerator /
        denominator
    ) * 100.0


def dedupe_keep_order(
    items: List[str],
) -> List[str]:

    return list(
        dict.fromkeys(
            items
        )
    )


def has_item(
    items: List[str],
    text: str,
) -> bool:

    target = (
        text
        .strip()
        .lower()
    )

    return any(
        i.strip().lower()
        == target

        for i in items
    )
