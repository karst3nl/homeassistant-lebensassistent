"""Centgenaue Textkonvertierung ohne Gleitkommaarithmetik."""

import re
from datetime import date

MIN_CENTS = -(2**63)
MAX_CENTS = 2**63 - 1


def parse_eur(text: str) -> int:
    if not isinstance(text, str) or len(text) > 32:
        raise ValueError("Bitte einen gültigen Eurobetrag eingeben.")
    match = re.fullmatch(r"([+-]?)([0-9]+)(?:[.,]([0-9]{1,2}))?", text.strip())
    if match is None:
        raise ValueError("Eurobetrag mit höchstens zwei Nachkommastellen eingeben.")
    sign, whole, fraction = match.groups()
    cents = int(whole) * 100 + int((fraction or "").ljust(2, "0"))
    if sign == "-":
        cents = -cents
    if not MIN_CENTS <= cents <= MAX_CENTS:
        raise ValueError("Der Betrag liegt außerhalb des unterstützten Bereichs.")
    return cents


def parse_date(text: str) -> date:
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text) is None:
        raise ValueError("Bitte ein gültiges Datum eingeben.")
    return date.fromisoformat(text)


def format_eur(cents: int) -> str:
    whole, fraction = divmod(abs(cents), 100)
    grouped = f"{whole:,}".replace(",", ".")
    return f"{'-' if cents < 0 else ''}{grouped},{fraction:02d} €"
