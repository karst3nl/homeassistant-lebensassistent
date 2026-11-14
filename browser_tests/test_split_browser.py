"""Kategorieaufteilung ohne Browser-JavaScript, nur synthetische Daten."""

import uuid
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Locator, expect

INGRESS_PREFIX = "/api/hassio_ingress/synthetic-browser-session"
SCENARIOS = [
    (
        prefix,
        width,
        theme,
        "income" if (prefix, width, theme) == ("", 1280, "dark") else "expense",
        False,
    )
    for prefix in ("", "/synthetic-ingress")
    for width in (390, 1280)
    for theme in ("light", "dark")
] + [(INGRESS_PREFIX, 390, "light", "expense", True)]


@pytest.mark.parametrize(("prefix", "width", "theme", "kind", "null_origin"), SCENARIOS)
def test_split_form_controls_sum_and_single_posting(
    browser: Browser,
    server_url: str,
    tmp_path: Path,
    prefix: str,
    width: int,
    theme: str,
    kind: str,
    null_origin: bool,
) -> None:
    context = browser.new_context(
        viewport={"width": width, "height": 900},
        color_scheme=theme,
        locale="de-DE",
        java_script_enabled=False,
    )
    page = context.new_page()
    suffix = uuid.uuid4().hex[:8]
    account_name = f"Synthetisches Aufteilungskonto {suffix}"
    categories = [f"Synthetische Teilkategorie {index} {suffix}" for index in (1, 2)]
    description = "<script>syntheticSplitDescription()</script>"
    memos = ["<b>Synthetische Teilnotiz A</b>", "<script>syntheticSplitMemo()</script>"]
    finance_url = f"{server_url}{prefix}/bereiche/finanzen"
    split_url = f"{server_url}{prefix}/buchungen/aufteilen"
    posted_statuses: list[int] = []

    def submit(button: Locator, expected: int) -> None:
        with page.expect_response(
            lambda response: (
                response.request.method == "POST" and response.url == split_url
            )
        ) as posted:
            button.click()
        response = posted.value
        assert response.status == expected
        if null_origin:
            headers = response.request.all_headers()
            assert headers.get("origin") == "null"
            assert headers.get("sec-fetch-site") == "same-origin"
        posted_statuses.append(response.status)

    try:
        page.goto(finance_url)
        page.get_by_label("Kontoname", exact=True).fill(account_name)
        page.get_by_label("Anfangssaldo in EUR", exact=True).fill("100,00")
        page.get_by_label("Startdatum", exact=True).fill("2026-01-01")
        page.get_by_role("button", name="Konto anlegen", exact=True).click()
        expect(page.get_by_role("status")).to_have_text("Konto angelegt.")
        for name in categories:
            page.get_by_label("Kategoriename", exact=True).fill(name)
            page.get_by_label("Art", exact=True).select_option(kind)
            page.get_by_role("button", name="Kategorie anlegen", exact=True).click()
            expect(page.get_by_role("status")).to_have_text("Kategorie angelegt.")

        with page.expect_response(split_url) as opened:
            page.get_by_role("link", name="Buchung aufteilen", exact=True).click()
        assert opened.value.status == 200
        if null_origin:
            assert opened.value.headers["referrer-policy"] == "no-referrer"
        expect(
            page.get_by_role("heading", name="Buchung aufteilen", exact=True)
        ).to_be_visible()
        page.get_by_label("Buchungsart", exact=True).select_option(kind)
        page.get_by_label("Buchungskonto", exact=True).select_option(label=account_name)
        page.get_by_label("Gesamtbetrag in EUR", exact=True).fill("100,00")
        page.get_by_label("Buchungsdatum", exact=True).fill("2026-01-15")
        page.get_by_label("Buchungsnotiz (optional)", exact=True).fill(description)
        for index, amount in ((1, "70,00"), (2, "29,99")):
            kind_label = "Einnahme" if kind == "income" else "Ausgabe"
            label = f"{categories[index - 1]} ({kind_label})"
            page.get_by_label(f"Kategorie {index}", exact=True).select_option(
                label=label
            )
            page.get_by_label(f"Betrag {index} in EUR", exact=True).fill(amount)
            page.get_by_label(f"Teilnotiz {index} (optional)", exact=True).fill(
                memos[index - 1]
            )
        submission = page.locator('input[name="submission_id"]').input_value()

        submit(
            page.get_by_role("button", name="Teilbetrag hinzufügen", exact=True), 200
        )
        expect(page.locator('input[name="row_count"]')).to_have_value("3")
        expect(page.get_by_label("Betrag 1 in EUR", exact=True)).to_have_value("70,00")
        expect(page.get_by_label("Teilnotiz 2 (optional)", exact=True)).to_have_value(
            memos[1]
        )
        page.get_by_label("Teilnotiz 3 (optional)", exact=True).fill(
            "Synthetisch entfernen"
        )
        submit(
            page.get_by_role("button", name="Teilbetrag 3 entfernen", exact=True), 200
        )
        expect(page.locator('input[name="row_count"]')).to_have_value("2")
        expect(page.locator('input[name="submission_id"]')).to_have_value(submission)
        expect(page.get_by_label("Kategorie 3", exact=True)).to_have_count(0)
        expect(page.get_by_label("Betrag 2 in EUR", exact=True)).to_have_value("29,99")
        expect(page.get_by_label("Buchungsnotiz (optional)", exact=True)).to_have_value(
            description
        )

        submit(page.get_by_role("button", name="Aufteilung speichern", exact=True), 422)
        expect(page.get_by_role("alert")).to_contain_text(
            "Die Summe der Teilbeträge muss dem Gesamtbetrag entsprechen."
        )
        expect(page.locator('input[name="submission_id"]')).to_have_value(submission)
        expect(page.get_by_label("Teilnotiz 1 (optional)", exact=True)).to_have_value(
            memos[0]
        )
        expect(page.get_by_label("Betrag 2 in EUR", exact=True)).to_have_value("29,99")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.locator("main").focus()
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=tmp_path / "split-form.png", full_page=True)

        check_page = context.new_page()
        try:
            check_page.goto(finance_url)
            account = check_page.get_by_role("article", name=account_name, exact=True)
            expect(account.locator("dd.amount")).to_have_text("100,00 €")
            expect(
                check_page.locator("#buchungen article").filter(has_text=account_name)
            ).to_have_count(0)
        finally:
            check_page.close()

        page.get_by_label("Betrag 2 in EUR", exact=True).fill("30,00")
        submit(page.get_by_role("button", name="Aufteilung speichern", exact=True), 303)
        expect(page.get_by_role("status")).to_have_text("Buchung gespeichert.")
        assert page.url.startswith(finance_url)
        account = page.get_by_role("article", name=account_name, exact=True)
        balance = "200,00 €" if kind == "income" else "0,00 €"
        expect(account.locator("dd.amount")).to_have_text(balance)
        bookings = page.locator("#buchungen article").filter(has_text=account_name)
        expect(bookings).to_have_count(1)
        expect(
            bookings.get_by_role("heading", name="Aufgeteilte Buchung", exact=True)
        ).to_be_visible()
        expect(bookings.locator(".record-heading > .amount")).to_have_text(
            "+100,00 €" if kind == "income" else "-100,00 €"
        )
        parts = bookings.get_by_role("list", name="Aufteilung", exact=True).get_by_role(
            "listitem"
        )
        expect(parts).to_have_count(2)
        for index, amount in ((0, "70,00 €"), (1, "30,00 €")):
            expect(parts.nth(index)).to_contain_text(categories[index])
            expect(parts.nth(index)).to_contain_text(memos[index])
            expect(parts.nth(index).locator("strong")).to_have_text(amount)
        expect(bookings).to_contain_text(description)
        assert bookings.locator("script, b").count() == 0
        page.reload()
        expect(bookings).to_have_count(1)
        expect(parts).to_have_count(2)
        expect(account.locator("dd.amount")).to_have_text(balance)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert posted_statuses == [200, 200, 422, 303]
        page.locator("main").focus()
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=tmp_path / "split-booking.png", full_page=True)
    finally:
        context.close()
