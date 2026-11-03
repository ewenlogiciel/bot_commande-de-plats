import os
import re
import sys
from playwright.sync_api import sync_playwright

URL_PORTAIL = "https://allresto.moneweb.fr"
USER = os.environ.get("BOT_USER")
PASS = os.environ.get("BOT_PASS")

# Mots-clés par ordre de priorité (le premier mot-clé qui trouve un article gagne).
# Les noms sur le site sont en majuscules sans accent ("PATE JAMBON EMMENTAL").
PLAT_PREFERE = "Poulet, Pate, Pâte"
DESSERT_1_PREFERE = "Banane, Pomme, gaufre, gauffre"
DESSERT_2_PREFERE = "Yaourt, compote, fruit"

DELAI_CLIC = 5000  # 5 secondes entre chaque étape


def nettoyer(nom):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", nom)


def attendre(page):
    """Attend que la page soit stable, puis fait une pause."""
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(DELAI_CLIC)


def cliquer(page, cible, nom, photo):
    """Attend la page, prend une capture, puis clique sur l'élément ciblé."""
    print(f"-> {nom}")
    attendre(page)
    page.screenshot(path=f"{photo}_{nettoyer(nom)}.png")
    cible.wait_for(state="visible", timeout=15000)
    cible.click()


def boutons_choisir(zone):
    return zone.get_by_text("Choisir", exact=True)


def choisir_etape(page, texte_preferences, nom_etape, photo, modale=False):
    """Clique sur le bouton 'Choisir' de la carte correspondant à un mot-clé,
    ou sur le 1er 'Choisir' dispo. Si modale=True, confirme aussi dans la modale."""
    print(f"Sélection en cours : {nom_etape}...")
    attendre(page)
    page.screenshot(path=f"{photo}_avant_{nettoyer(nom_etape)}.png")

    mots_cles = [m.strip() for m in texte_preferences.split(",") if m.strip()]
    bouton = None

    for mot in mots_cles:
        titres = page.get_by_text(re.compile(re.escape(mot), re.I)).filter(visible=True)
        for i in range(min(titres.count(), 10)):
            # Plus proche conteneur du titre qui contient un bouton "Choisir"
            carte = titres.nth(i).locator(
                "xpath=ancestor::*[.//*[contains(normalize-space(.), 'Choisir')]][1]"
            )
            candidats = boutons_choisir(carte)
            # Une vraie carte n'a qu'un seul bouton (sinon on est sur un conteneur trop large)
            if candidats.count() == 1:
                print(f"-> {nom_etape} trouvé avec le mot-clé : {mot}")
                bouton = candidats.first
                break
        if bouton is not None:
            break

    if bouton is None:
        print(f"-> Aucun favori trouvé pour {nom_etape}, sélection du 1er choix dispo.")
        bouton = boutons_choisir(page).filter(visible=True).first

    bouton.click()

    if modale:
        # Une modale s'ouvre : il faut recliquer sur "Choisir" dedans
        page.wait_for_timeout(2000)
        page.screenshot(path=f"{photo}_modale_{nettoyer(nom_etape)}.png")
        modale_visible = page.locator(".modal-dialog, [role='dialog'], .modal").filter(visible=True)
        if modale_visible.count() > 0:
            boutons_choisir(modale_visible.last).first.click()
        else:
            # Plan B : la modale est en fin de page, donc son bouton est le dernier visible
            boutons_choisir(page).filter(visible=True).last.click()
        print(f"-> {nom_etape} : confirmé dans la modale.")


def commander():
    if not USER or not PASS:
        print("ERREUR : BOT_USER / BOT_PASS non définis.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
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

            # 2. Bouton "RÉSERVER" du tableau de bord
            bouton_reserver = page.locator(
                'a.btn-block[ui-sref="authenticated.ok.create-reservation"]'
            )
            cliquer(page, bouton_reserver, "2_Reserver", "01")

            # 3. Service : "CASIER LILLE : Wenov Euratech (midi)"
            service = page.get_by_text(re.compile(r"Wenov Euratech", re.I)).first
            cliquer(page, service, "3_Service_Wenov", "02")

            # 4. Lieu de livraison : "Casier Wenov ..." mais PAS "Casier Wenov PMR ..."
            lieu = page.get_by_text(re.compile(r"Casier Wenov(?!\s+PMR)", re.I)).first
            cliquer(page, lieu, "4_Lieu_livraison_sans_PMR", "03")

            # 5. Offre : tuile "Formules"
            offre = page.get_by_text(re.compile(r"^\s*Formules\s*$", re.I)).first
            cliquer(page, offre, "5_Offre_Formules", "04")

            # 6. Formule : "FORMULE CLICK & COLLECT CASIER"
            formule = page.get_by_text(
                re.compile(r"FORMULE CLICK\s*&\s*COLLECT CASIER", re.I)
            ).first
            cliquer(page, formule, "6_Formule_Click_Collect", "05")

            # 7. Plat (avec modale) puis 2 desserts (sans modale, passage direct à la suite)
            choisir_etape(page, PLAT_PREFERE, "Plat", "06", modale=True)
            choisir_etape(page, DESSERT_1_PREFERE, "Dessert 1", "07")
            choisir_etape(page, DESSERT_2_PREFERE, "Dessert 2", "08")

            # 8. Bouton "Réserver" en bas de la page (pas "Continuer ma réservation")
            reserver = page.get_by_text(re.compile(r"^\s*Réserver\s*$", re.I)).filter(visible=True).first
            cliquer(page, reserver, "8_Reserver_final", "09")

            # 9. Panier : "Valider et payer"
            valider = page.get_by_text(re.compile(r"Valider et payer", re.I)).filter(visible=True).first
            cliquer(page, valider, "9_Valider_et_payer", "10")

            # 10. Paiement : "Payer 1,00 €"  (dernier clic, irréversible)
            payer = page.get_by_text(re.compile(r"^\s*Payer\s+\d", re.I)).filter(visible=True).first
            cliquer(page, payer, "10_Payer", "11")
            print("Clic sur Payer effectué.")

        except Exception as e:
            print(f"ERREUR CRITIQUE : {e}")
            print(f"URL au moment du bug : {page.url}")
            try:
                page.screenshot(path="99_ERREUR_SCREENSHOT.png", full_page=True)
                with open("99_ERREUR_PAGE.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
            except Exception:
                pass
            browser.close()
            sys.exit(1)

        # Le paiement est cliqué : à partir d'ici on ne doit JAMAIS échouer,
        # sinon la tentative suivante recommanderait (doublon).
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(DELAI_CLIC)
            page.screenshot(path="12_succes_final.png")
        except Exception as e:
            print(f"Avertissement après paiement (ignoré) : {e}")

        print("Commande payée avec succès !")
        browser.close()


if __name__ == "__main__":
    commander()