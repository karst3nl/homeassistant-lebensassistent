"""Native Formular-POSTs unter synthetischer HA-no-referrer-Antwortpolicy."""

import uuid

from playwright.sync_api import Browser, Locator, expect

INGRESS_PREFIX = "/api/hassio_ingress/synthetic-browser-session"


def test_ingress_forms_with_home_assistant_referrer_policy(
    browser: Browser, server_url: str
) -> None:
    context = browser.new_context(
        viewport={"width": 390, "height": 900}, locale="de-DE"
    )
    page = context.new_page()
    prefix_url = f"{server_url}{INGRESS_PREFIX}"
    suffix = uuid.uuid4().hex[:8]
    name = f"Synthetisches Ingress-Konto {suffix}"
    category_name = f"Synthetische Ingress-Kategorie {suffix}"
    posts = []

    def submit(button: Locator) -> None:
        with page.expect_response(
            lambda response: response.request.method == "POST"
        ) as posted:
            button.click()
        response = posted.value
        headers = response.request.all_headers()
        assert headers.get("origin") == "null"
        assert headers.get("sec-fetch-site") == "same-origin"
        assert response.url.startswith(f"{prefix_url}/")
        assert response.status == 303
        posts.append(response.url)

    try:
        page.goto(server_url)
        with page.expect_response(f"{prefix_url}/bereiche/finanzen") as initial:
            page.set_content(
                f'<iframe id="synthetic-ingress" title="Synthetische HA-App" '
                f'src="{prefix_url}/bereiche/finanzen"></iframe>'
            )
        assert initial.value.headers["referrer-policy"] == "no-referrer"
        frame = page.frame_locator("#synthetic-ingress")
        frame.get_by_label("Kontoname", exact=True).fill(name)
        frame.get_by_label("Anfangssaldo in EUR", exact=True).fill("-12,34")
        frame.get_by_label("Startdatum", exact=True).fill("2026-01-15")
        submit(frame.get_by_role("button", name="Konto anlegen", exact=True))
        account = frame.get_by_role("article", name=name, exact=True)
        expect(account).to_contain_text("-12,34 €")
        submit(account.get_by_role("button", name="Archivieren", exact=True))
        expect(account).to_contain_text("Archiviert")
        submit(account.get_by_role("button", name="Aktivieren", exact=True))
        expect(account).to_contain_text("Aktiv")

        frame.get_by_label("Kategoriename", exact=True).fill(category_name)
        frame.get_by_label("Art", exact=True).select_option("expense")
        submit(frame.get_by_role("button", name="Kategorie anlegen", exact=True))
        category = frame.get_by_role(
            "article", name=f"Kategorie {category_name}", exact=True
        )
        expect(category).to_contain_text("Ausgabe")
        submit(category.get_by_role("button", name="Archivieren", exact=True))
        expect(category).to_contain_text("Archiviert")
        submit(category.get_by_role("button", name="Aktivieren", exact=True))
        expect(category).to_contain_text("Aktiv")
        assert len(posts) == 6
    finally:
        context.close()
