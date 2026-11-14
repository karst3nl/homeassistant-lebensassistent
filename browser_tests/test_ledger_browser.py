"""Normale Einnahmen/Ausgaben im echten Browser mit synthetischen Testdaten."""

import uuid
from pathlib import Path

import pytest
from playwright.sync_api import Browser, expect

INGRESS_PREFIX = "/api/hassio_ingress/synthetic-browser-session"
SCENARIOS = [
    (prefix, width, theme, False)
    for prefix in ("", "/synthetic-ingress")
    for width in (390, 1280)
    for theme in ("light", "dark")
] + [(INGRESS_PREFIX, 390, "light", True)]


@pytest.mark.parametrize(("prefix", "width", "theme", "null_origin"), SCENARIOS)
def test_income_expense_and_future_booking(
    browser: Browser,
    server_url: str,
    tmp_path: Path,
    prefix: str,
    width: int,
    theme: str,
    null_origin: bool,
) -> None:
    context = browser.new_context(
        viewport={"width": width, "height": 900}, color_scheme=theme, locale="de-DE"
    )
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    suffix = uuid.uuid4().hex[:8]
    account_name = f"Synthetisches Buchungskonto {suffix}"
    expense_name = f"Synthetische Ausgabe {suffix}"
    income_name = f"Synthetische Einnahme {suffix}"
    note = "<script>window.syntheticLedgerInjected = true</script>"
    requests: list[str] = []

    def submit_posting(expected: int = 303) -> None:
        with page.expect_response(
            lambda response: (
                response.request.method == "POST"
                and response.url == f"{server_url}{prefix}/buchungen"
            )
        ) as posted:
            page.get_by_role("button", name="Buchung speichern", exact=True).click()
        response = posted.value
        assert response.status == expected
        if null_origin:
            headers = response.request.all_headers()
            assert headers.get("origin") == "null"
            assert headers.get("sec-fetch-site") == "same-origin"
        requests.append(response.url)
        if expected == 303:
            expect(page.get_by_role("status")).to_have_text("Buchung gespeichert.")

    def fill_posting(
        kind: str, category_name: str, amount: str, booked_date: str
    ) -> None:
        page.get_by_label("Buchungsart", exact=True).select_option(kind)
        page.get_by_label("Buchungskonto", exact=True).select_option(label=account_name)
        label = f"{category_name} ({'Einnahme' if kind == 'income' else 'Ausgabe'})"
        page.get_by_label("Buchungskategorie", exact=True).select_option(label=label)
        page.get_by_label("Buchungsbetrag in EUR", exact=True).fill(amount)
        page.get_by_label("Buchungsdatum", exact=True).fill(booked_date)

    try:
        response = page.goto(f"{server_url}{prefix}/bereiche/finanzen")
        assert response is not None and response.status == 200
        if null_origin:
            assert response.headers["referrer-policy"] == "no-referrer"
        page.get_by_label("Kontoname", exact=True).fill(account_name)
        page.get_by_label("Kontoart", exact=True).select_option("checking")
        page.get_by_label("Anfangssaldo in EUR", exact=True).fill("100,00")
        page.get_by_label("Startdatum", exact=True).fill("2026-01-01")
        page.get_by_role("button", name="Konto anlegen", exact=True).click()
        expect(page.get_by_role("status")).to_have_text("Konto angelegt.")
        for name, kind in ((expense_name, "expense"), (income_name, "income")):
            page.get_by_label("Kategoriename", exact=True).fill(name)
            page.get_by_label("Art", exact=True).select_option(kind)
            page.get_by_role("button", name="Kategorie anlegen", exact=True).click()
            expect(page.get_by_role("status")).to_have_text("Kategorie angelegt.")

        account = page.get_by_role("article", name=account_name, exact=True)
        expect(account.locator("dd.amount")).to_have_text("100,00 €")
        fill_posting("expense", expense_name, "1,001", "2026-01-02")
        page.get_by_label("Buchungsnotiz (optional)").fill(note)
        submission = page.locator('input[name="submission_id"]').input_value()
        account_id = page.get_by_label("Buchungskonto", exact=True).input_value()
        category_id = page.get_by_label("Buchungskategorie", exact=True).input_value()
        submit_posting(422)
        expect(page.get_by_role("alert")).to_contain_text(
            "höchstens zwei Nachkommastellen"
        )
        expect(page.get_by_label("Buchungskonto", exact=True)).to_have_value(account_id)
        expect(page.get_by_label("Buchungskategorie", exact=True)).to_have_value(
            category_id
        )
        expect(page.get_by_label("Buchungsnotiz (optional)")).to_have_value(note)
        expect(page.locator('input[name="submission_id"]')).to_have_value(submission)
        expect(account.locator("dd.amount")).to_have_text("100,00 €")

        page.get_by_label("Buchungsbetrag in EUR", exact=True).fill("12,34")
        submit_posting()
        expect(account.locator("dd.amount")).to_have_text("87,66 €")
        bookings = page.locator("#buchungen article").filter(has_text=account_name)
        expect(bookings).to_have_count(1)
        expect(bookings.first).to_contain_text(note)
        assert page.evaluate("typeof window.syntheticLedgerInjected") == "undefined"
        assert page.locator('input[name="submission_id"]').input_value() != submission

        fill_posting("income", income_name, "0,01", "2026-01-03")
        submit_posting()
        expect(account.locator("dd.amount")).to_have_text("87,67 €")
        fill_posting("income", income_name, "25,00", "2099-01-01")
        submit_posting()
        expect(bookings).to_have_count(3)
        expect(bookings.first).to_contain_text("Zukünftig datiert")
        expect(bookings.first).to_contain_text("01.01.2099")
        expect(account.locator("dd.amount")).to_have_text("87,67 €")
        expect(account).to_contain_text("100,00 €")
        page.reload()
        expect(bookings).to_have_count(3)
        expect(account.locator("dd.amount")).to_have_text("87,67 €")
        assert page.url.startswith(f"{server_url}{prefix}/bereiche/finanzen")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert len(requests) == 4
        assert not errors, errors
        page.locator("main").focus()
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=tmp_path / "ledger.png", full_page=True)
    finally:
        context.close()
