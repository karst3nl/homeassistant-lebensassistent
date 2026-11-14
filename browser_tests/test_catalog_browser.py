"""Bedienbare Konten-/Kategorienmasken in echten Browsern, nur synthetische Daten."""

import uuid
from pathlib import Path

import pytest
from playwright.sync_api import Browser, expect


@pytest.mark.parametrize("prefix", ["", "/synthetic-ingress"])
@pytest.mark.parametrize("width", [390, 1280])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_account_and_category_forms(
    browser: Browser,
    server_url: str,
    tmp_path: Path,
    prefix: str,
    width: int,
    theme: str,
) -> None:
    context = browser.new_context(
        viewport={"width": width, "height": 900}, color_scheme=theme, locale="de-DE"
    )
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    suffix = uuid.uuid4().hex[:8]
    name = f"Synthetisches Konto {suffix}"
    category_name = f"Synthetische Kategorie {suffix}"
    try:
        page.goto(f"{server_url}{prefix}/bereiche/finanzen")
        expect(
            page.get_by_role("heading", name="Konten & Kategorien", exact=True)
        ).to_be_visible()
        page.get_by_label("Kontoname", exact=True).fill(name)
        page.get_by_label("Kontoart", exact=True).select_option("checking")
        page.get_by_label("Anfangssaldo in EUR", exact=True).fill("1,001")
        page.get_by_label("Startdatum", exact=True).fill("2026-01-15")
        page.get_by_role("button", name="Konto anlegen", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text(
            "höchstens zwei Nachkommastellen"
        )
        expect(page.get_by_label("Kontoname", exact=True)).to_have_value(name)
        page.get_by_label("Anfangssaldo in EUR", exact=True).fill("-12,34")
        page.get_by_role("button", name="Konto anlegen", exact=True).click()
        expect(page.get_by_role("status")).to_have_text("Konto angelegt.")
        account = page.get_by_role("article", name=name, exact=True)
        expect(account).to_contain_text("-12,34 €")
        expect(account).to_contain_text("15.01.2026")
        assert account.get_by_role("textbox").count() == 0
        account.get_by_role("button", name="Archivieren", exact=True).click()
        expect(account).to_contain_text("Archiviert")
        account.get_by_role("button", name="Aktivieren", exact=True).click()
        expect(account).to_contain_text("Aktiv")
        expect(account).to_contain_text("-12,34 €")

        page.get_by_label("Kategoriename", exact=True).fill(category_name)
        page.get_by_label("Art", exact=True).select_option("expense")
        page.get_by_role("button", name="Kategorie anlegen", exact=True).click()
        category = page.get_by_role(
            "article", name=f"Kategorie {category_name}", exact=True
        )
        expect(category).to_contain_text("Ausgabe")
        category.get_by_role("button", name="Archivieren", exact=True).click()
        expect(category).to_contain_text("Archiviert")
        category.get_by_role("button", name="Aktivieren", exact=True).click()
        page.reload()
        expect(category).to_contain_text("Aktiv")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.url.startswith(f"{server_url}{prefix}/bereiche/finanzen")
        page.locator("main").focus()
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=tmp_path / "finance.png", full_page=True)
        assert not errors, errors
    finally:
        context.close()


def test_names_and_notes_cannot_execute_script(
    browser: Browser, server_url: str
) -> None:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    try:
        page.goto(f"{server_url}/bereiche/finanzen")
        name = f"Synthetisch <b>{uuid.uuid4().hex[:8]}</b>"
        note = "<script>window.syntheticInjected = true</script>"
        page.get_by_label("Kontoname", exact=True).fill(name)
        page.get_by_label("Anfangssaldo in EUR", exact=True).fill("0,01")
        page.get_by_label("Notiz (optional)").fill(note)
        page.get_by_role("button", name="Konto anlegen", exact=True).click()
        expect(page.get_by_role("article", name=name, exact=True)).to_contain_text(note)
        assert page.evaluate("typeof window.syntheticInjected") == "undefined"
    finally:
        context.close()
