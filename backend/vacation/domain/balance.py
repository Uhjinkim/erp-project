"""Map leave request types to the balance they consume."""


def balance_type_id(type_id: str) -> str:
    """Half-day leave consumes the annual-leave balance, not a separate pool."""
    return "ANNUAL" if type_id == "HALF" else type_id
