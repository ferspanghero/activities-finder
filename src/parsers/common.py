"""Small formatting helpers shared by parsers."""


def _amount(value: str | float | None) -> float | None:
    if value is None or value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def _money(amount: float) -> str:
    return f"${amount:.2f}".replace(".00", "")


def format_price(low: str | float | None, high: str | float | None) -> str | None:
    """Format a source price range as 'Free', '$15', '$15–$25', or 'Free–$25'; None when unknown.

    A zero upper bound means "no upper bound given", as Daily Hive reports single prices.
    """
    lo, hi = _amount(low), _amount(high)

    if lo is None and hi is None:
        return None

    if not lo and not hi:
        return "Free"

    if lo == 0 and hi:
        return f"Free–{_money(hi)}"

    low_amount = lo or hi or 0.0
    high_amount = hi if hi and hi > low_amount else low_amount

    if low_amount == high_amount:
        return _money(low_amount)

    return f"{_money(low_amount)}–{_money(high_amount)}"
