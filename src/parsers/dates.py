"""Date helpers shared by parsers whose listings omit the year."""

from datetime import date


def infer_year(month: int, day: int, ref: date) -> date | None:
    """Return the month/day occurrence closest to `ref`, trying ref's year and its neighbours.

    Handles listings that roll over from December into January. Returns None when
    the month/day exists in none of the candidate years (e.g. Feb 30).
    """
    candidates = []

    for year in (ref.year - 1, ref.year, ref.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            continue

    if not candidates:
        return None

    return min(candidates, key=lambda d: abs((d - ref).days))
