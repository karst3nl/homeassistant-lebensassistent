"""Geld und Datumswerte ausschließlich aus synthetischen Texteingaben."""

from datetime import date

import pytest

from lebensassistent.services.values import format_eur, parse_date, parse_eur


@pytest.mark.parametrize(
    ("text", "cents"),
    [
        ("0", 0),
        ("1234,56", 123456),
        ("-12.01", -1201),
        ("+1,2", 120),
        ("-0,01", -1),
        ("92233720368547758,07", 9223372036854775807),
        ("-92233720368547758,08", -9223372036854775808),
    ],
)
def test_parse_eur_is_cent_exact(text: str, cents: int) -> None:
    assert parse_eur(text) == cents


@pytest.mark.parametrize(
    "text",
    [
        "",
        "1,001",
        "1.234,56",
        "1e3",
        "NaN",
        "Infinity",
        "true",
        "92233720368547758,08",
        "-92233720368547758,09",
        "1,",
        ".12",
    ],
)
def test_invalid_amounts_are_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        parse_eur(text)


def test_currency_format_uses_integer_arithmetic() -> None:
    assert format_eur(-123456) == "-1.234,56 €"
    assert format_eur(-1) == "-0,01 €"


@pytest.mark.parametrize(
    "text", ["2026-02-29", "2026-13-01", "20260101", "2026-1-1", "today"]
)
def test_invalid_dates_are_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        parse_date(text)


def test_real_calendar_dates_including_future_are_supported() -> None:
    assert parse_date("2024-02-29") == date(2024, 2, 29)
    assert parse_date("2099-01-01") == date(2099, 1, 1)
