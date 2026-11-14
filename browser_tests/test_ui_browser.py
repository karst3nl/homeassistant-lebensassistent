"""Navigation, Assets, Fehler und Themes im echten Browser mit synthetischen URLs."""

from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Browser, Route, expect


@pytest.mark.parametrize("prefix", ["", "/synthetic-ingress"])
@pytest.mark.parametrize("width", [320, 390, 768, 1280])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_responsive_navigation_and_theme(
    browser: Browser,
    server_url: str,
    tmp_path: Path,
    prefix: str,
    width: int,
    theme: str,
) -> None:
    context = browser.new_context(
        viewport={"width": width, "height": 900}, color_scheme=theme
    )
    errors: list[str] = []
    external: list[str] = []

    def local_only(route: Route) -> None:
        if urlsplit(route.request.url).hostname != "127.0.0.1":
            external.append(route.request.url)
            route.abort()
        else:
            route.continue_()

    context.route("**/*", local_only)
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "console",
        lambda message: (
            errors.append(message.text) if message.type == "error" else None
        ),
    )
    page.on(
        "response",
        lambda response: (
            errors.append(f"{response.status}: {response.url}")
            if response.status >= 400
            else None
        ),
    )
    try:
        page.goto(f"{server_url}{prefix}/", wait_until="networkidle")
        expect(page.get_by_role("heading", level=1)).to_have_text(
            "Dein Alltag.Gut geordnet."
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        background = page.locator("body").evaluate(
            "el => getComputedStyle(el).backgroundColor"
        )
        channels = [int(value.strip()) for value in background[4:-1].split(",")]
        assert (sum(channels) / 3 < 100) == (theme == "dark")

        page.keyboard.press("Tab")
        skip = page.get_by_role("link", name="Zum Inhalt springen")
        expect(skip).to_be_focused()
        page.keyboard.press("Enter")
        expect(page.locator("main")).to_be_focused()

        navigation = page.get_by_role("navigation", name="Hauptnavigation")
        destinations = navigation.get_by_role("link").evaluate_all(
            "links => links.map(link => ({href: link.getAttribute('href'), "
            "label: link.textContent.trim()}))"
        )
        assert len(destinations) == 8
        for destination in destinations:
            navigation.get_by_role(
                "link", name=destination["label"], exact=True
            ).click()
            assert urlsplit(page.url).path == destination["href"]
            assert destination["href"] == f"{prefix}/" or destination[
                "href"
            ].startswith(f"{prefix}/bereiche/")
            expect(navigation.locator('[aria-current="page"]')).to_have_text(
                destination["label"]
            )
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        page.goto(f"{server_url}{prefix}/", wait_until="networkidle")
        page.screenshot(path=tmp_path / "overview.png", full_page=True)
        assert not errors, errors
        assert not external, external
    finally:
        context.close()


@pytest.mark.parametrize("prefix", ["", "/synthetic-ingress"])
def test_browser_error_and_live_theme(
    browser: Browser, server_url: str, prefix: str
) -> None:
    context = browser.new_context(
        viewport={"width": 390, "height": 844}, color_scheme="light"
    )
    page = context.new_page()
    try:
        response = page.goto(f"{server_url}{prefix}/not-a-real-page")
        assert response is not None and response.status == 404
        expect(page.get_by_role("heading", level=1)).to_have_text(
            "Seite nicht gefunden"
        )
        page.get_by_role("link", name="Zur Übersicht", exact=True).click()
        assert urlsplit(page.url).path == f"{prefix}/"
        before = page.locator("body").evaluate(
            "el => getComputedStyle(el).backgroundColor"
        )
        page.emulate_media(color_scheme="dark")
        after = page.locator("body").evaluate(
            "el => getComputedStyle(el).backgroundColor"
        )
        assert before != after
    finally:
        context.close()
