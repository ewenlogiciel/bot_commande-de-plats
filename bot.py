import os
import re
import sys
from playwright.sync_api import sync_playwright

URL_PORTAIL = "https://allresto.moneweb.fr"
USER = os.environ.get("BOT_USER")
PASS = os.environ.get("BOT_PASS")

LIEU_RETRAIT = "Wenov"
PLAT_PREFERE = "Poulet, Pâtes"
DESSERT_1_PREFERE = "Banane, Pomme, gaufre, gauffre"
DESSERT_2_PREFERE = "Yaourt, compote, fruit"

DELAI_CLIC = 5000  # 5000 ms = 5 secondes entre chaque étape


def choisir_etape(page, texte_preferences, nom_etape, num_photo):
    """Sélectionne un article selon tes mots-clés, ou prend le 1er dispo."""
    print(f"Sélection en cours : {nom_etape}...")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(DELAI_CLIC)
    page.screenshot(path=f"{num_photo}_avant_{nom_etape.replace(' ', '_')}.png")

    mots_cles = [mot.strip() for mot in texte_preferences.split(",") if mot.strip()]

    choix_trouve = False
    for mot in mots_cles:
        element = page.locator(f"text=/{mot}/i").first
        if element.is_visible():
            print(f"-> {nom_etape} trouvé avec le mot-clé : {mot}")
            element.click()
            choix_trouve = True
            break

    if not choix_trouve:
        print(f"-> Aucun favori trouvé pour {nom_etape}, sélection du 1er choix dispo.")
        vignettes = page.locator(
            "main [ng-click], .container [ng-click], .thumbnail, .card, .list-group-item"
        ).or_(page.get_by_text(re.compile("Choisir|Ajouter", re.I)))
        vignettes.first.click()


def choisir_point_retrait_sans_pmr(page):
    """Choisit le point de retrait qui N'EST PAS l'accès handicapé."""
    print("Sélection du point de retrait (exclusion accès handicapé)...")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(DELAI_CLIC)
    page.screenshot(path="03_choix_point_retrait.png")

    btn_handicap = page.locator("text=/handicap|pmr/i").first
    if btn_handicap.is_visible():
        conteneur_choix = btn_handicap.locator(
            "xpath=ancestor::div[contains(@class, 'row') or contains(@class, 'list') or count(*) >= 2][1]"
        )
        autre_choix = conteneur_choix.locator(":scope > *").filter(
            has_not=page.locator("text=/handicap|pmr/i")
        ).first
        if autre_choix.is_visible():
            autre_choix.click()
            print("Point de retrait standard sélectionné !")
            return

    vignettes = page.locator('[ng-click], .btn, .card, .thumbnail, .list-group-item, a').filter(
        has_not_text=re.compile("handicap|pmr", re.I)
    )
    vignettes.first.click()
    print("Premier point de retrait sélectionné !")


def commander():
    if not USER or not PASS:
        print("ERREUR : BOT_USER / BOT_PASS non définis.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        try:
            # 1. Connexion
            print("1. Connexion à Moneweb...")
            page.goto(URL_PORTAIL)
            page.wait_for_selector("#formLogin__ctrl_Model_ID", timeout=15000)
            page.fill("#formLogin__ctrl_Model_ID", USER)
            page.fill("#formLogin__ctrl_Model_Password", PASS)
            page.press("#formLogin__ctrl_Model_Password", "Enter")

            # 2. Bouton "RÉSERVER"
            print("2. Attente du bouton Réserver...")
            bouton_reserver = 'a.btn-block[ui-sref="authenticated.ok.create-reservation"]'
            page.wait_for_selector(bouton_reserver, state="visible", timeout=15000)
            page.wait_for_timeout(DELAI_CLIC)
            page.screenshot(path="01_connecte_dashboard.png")
            page.click(bouton_reserver)

            # 3. Lieu
            print(f"3. Sélection du lieu contenant '{LIEU_RETRAIT}'...")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(DELAI_CLIC)
            page.screenshot(path="02_choix_lieu_wenov.png")
            lieu = page.locator(f"text=/{LIEU_RETRAIT}/i").first
            lieu.wait_for(state="visible", timeout=10000)
            lieu.click()

            # 4. Point de retrait
            choisir_point_retrait_sans_pmr(page)

            # 5. Plat + desserts
            choisir_etape(page, PLAT_PREFERE, "Plat", "04")
            choisir_etape(page, DESSERT_1_PREFERE, "Dessert 1", "05")
            choisir_etape(page, DESSERT_2_PREFERE, "Dessert 2", "06")

            # 6. Confirmation finale
            print("6. Confirmation finale de la commande...")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(DELAI_CLIC)
            page.screenshot(path="07_avant_confirmation.png")
            page.locator("text=/Confirmer|Valider|Commander/i").first.click()
            print("Clic de confirmation effectué.")

        except Exception as e:
            print(f"ERREUR CRITIQUE : {e}")
            print(f"URL au moment du bug : {page.url}")
            try:
                page.screenshot(path="99_ERREUR_SCREENSHOT.png", full_page=True)
            except Exception:
                pass
            browser.close()
            sys.exit(1)

        # La commande est validée : à partir d'ici, on ne doit JAMAIS échouer,
        # sinon la tentative suivante recommanderait (doublon).
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(DELAI_CLIC)
            page.screenshot(path="08_succes_final.png")
        except Exception as e:
            print(f"Avertissement après validation (ignoré) : {e}")

        print("Commande complète validée avec succès !")
        browser.close()


if __name__ == "__main__":
    commander()