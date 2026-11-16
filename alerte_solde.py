"""Envoie un e-mail récapitulatif après une commande réussie.

Contenu : ce qui a été choisi, le solde restant (avec un avertissement s'il est bas)
et en pièces jointes les captures des plats et desserts disponibles au moment de la commande.

Fichiers lus : solde.txt, choix.txt (écrits par bot.py) et 06/07/08_avant_*.png.
Variables d'environnement : MAIL_USER, MAIL_PASS, MAIL_TO (facultatif),
SEUIL_SOLDE, MAIL_A_CHAQUE_COMMANDE ("true" = un mail à chaque commande,
"false" = seulement si le solde est bas).
"""
import glob
import os
import smtplib
import sys
from email.message import EmailMessage

SEUIL = float(os.environ.get("SEUIL_SOLDE", "1.00"))
USER = os.environ.get("MAIL_USER")
PASS = os.environ.get("MAIL_PASS")
DEST = os.environ.get("MAIL_TO") or USER
A_CHAQUE_COMMANDE = os.environ.get("MAIL_A_CHAQUE_COMMANDE", "true").lower() == "true"


def euros(valeur):
    return f"{valeur:.2f}".replace(".", ",") + " €"


def lire(fichier):
    try:
        with open(fichier, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def main():
    try:
        solde = float(lire("solde.txt"))
    except ValueError:
        solde = None
    bas = solde is not None and solde <= SEUIL

    print(f"Solde après commande : {euros(solde) if solde is not None else 'inconnu'} "
          f"(seuil d'alerte : {euros(SEUIL)})")
    if not bas and not A_CHAQUE_COMMANDE:
        print("Solde suffisant et mail à chaque commande désactivé : rien à envoyer.")
        return

    if not USER or not PASS:
        print("ERREUR : secrets MAIL_USER / MAIL_PASS non définis, e-mail non envoyé.")
        sys.exit(1)

    choix = lire("choix.txt")
    captures = sorted(glob.glob("0[678]_avant_*.png"))

    lignes = ["Ta commande d'aujourd'hui est passée.", ""]
    if choix:
        lignes += ["Ce qui a été choisi :", choix, ""]
    if solde is not None:
        lignes.append(f"Solde restant : {euros(solde)}")
        if bas:
            lignes += ["", "Attention : solde bas, pense à recharger ton compte avant la "
                           "prochaine commande : https://allresto.moneweb.fr"]
    if captures:
        lignes += ["", "En pièces jointes : les plats et desserts disponibles au moment "
                       "de la commande (pour affiner tes mots-clés)."]
    else:
        lignes += ["", "(Aucune capture trouvée à joindre.)"]

    msg = EmailMessage()
    if bas:
        msg["Subject"] = f"Cantine : commande passée, il te reste {euros(solde)} (à recharger)"
    elif solde is not None:
        msg["Subject"] = f"Cantine : commande passée (solde {euros(solde)})"
    else:
        msg["Subject"] = "Cantine : commande passée"
    msg["From"] = USER
    msg["To"] = DEST
    msg.set_content("\n".join(lignes) + "\n")

    for chemin in captures:
        with open(chemin, "rb") as f:
            msg.add_attachment(f.read(), maintype="image", subtype="png",
                               filename=os.path.basename(chemin))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as smtp:
        smtp.login(USER, PASS)
        smtp.send_message(msg)
    print(f"E-mail envoyé à {DEST} ({len(captures)} capture(s) jointe(s)).")


if __name__ == "__main__":
    main()