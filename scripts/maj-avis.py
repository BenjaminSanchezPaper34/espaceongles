#!/usr/bin/env python3
"""Met à jour les avis affichés sur le site à partir de la page publique Planity.

Source : les données structurées (JSON-LD) publiées par Planity sur
https://www.planity.com/espace-ongles-34120-pezenas — note moyenne, nombre d'avis
et les 20 derniers avis (anonymes). Aucune API, aucun script tiers chez le visiteur :
le HTML est réécrit ici puis déployé (tâche GitHub hebdomadaire).

Régénère, entre les marqueurs AVIS:* :
- index.html : badges Planity + Google, carrousel d'avis, liens d'appel
- llms.txt   : section « Avis clientes » lisible par les moteurs IA

Note Google : saisie à la main dans data/avis-google.json (pas d'API ouverte).
Volontairement AUCUN aggregateRating en JSON-LD : Google interdit les avis
« auto-déclarés » d'un établissement sur son propre site.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
URL_PLANITY = "https://www.planity.com/espace-ongles-34120-pezenas"
NB_AVIS_PLANITY = 8          # avis Planity affichés dans le carrousel
LONGUEUR_MIN = 40            # on écarte les avis trop courts (« Au top »)


def lire_planity():
    req = urllib.request.Request(URL_PLANITY, headers={"User-Agent": "Mozilla/5.0 (espace-ongles.fr maj-avis)"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    for bloc in re.findall(r'application/ld\+json"?>(.*?)</script>', page, re.S):
        try:
            d = json.loads(bloc)
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict) and d.get("aggregateRating"):
            return d
    sys.exit("Données Planity introuvables : la page a peut-être changé de structure.")


def etoiles(note):
    pleines = round(note)
    return "&#9733;" * pleines + "&#9734;" * (5 - pleines)


def fr(note):
    return f"{note:.1f}".replace(".", ",")


def remplacer(texte, cle, contenu):
    motif = re.compile(rf"(<!-- AVIS:{cle}[^>]*-->\n).*?(\s*<!-- /AVIS:{cle} -->)", re.S)
    if not motif.search(texte):
        sys.exit(f"Marqueur AVIS:{cle} absent.")
    return motif.sub(lambda m: m.group(1) + contenu + m.group(2), texte, count=1)


def carte(texte, auteur, plateforme):
    return (
        '        <div class="review-card">\n'
        '          <div class="review-card-stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>\n'
        f'          <p class="review-card-text">{html.escape(texte, quote=False)}</p>\n'
        f'          <p class="review-card-author">{html.escape(auteur, quote=False)}</p>\n'
        f'          <p class="review-card-platform">{plateforme}</p>\n'
        "        </div>\n"
    )


def main():
    d = lire_planity()
    note_p = float(d["aggregateRating"]["ratingValue"])
    nb_p = int(d["aggregateRating"]["reviewCount"])
    g = json.loads((RACINE / "data/avis-google.json").read_text())
    note_g, nb_g, lien_g = g["google"]["note"], g["google"]["nombre"], g["google"]["lien"]

    planity = []
    for r in d.get("review", []):
        texte = " ".join(r.get("reviewBody", "").split())
        if float(r.get("reviewRating", {}).get("ratingValue", 0)) >= 5 and len(texte) >= LONGUEUR_MIN:
            j = date.fromisoformat(r["datePublished"][:10])
            planity.append((texte, j))
        if len(planity) == NB_AVIS_PLANITY:
            break

    badges = (
        '      <div class="reviews-badges">\n'
        f'        <a href="{URL_PLANITY}" target="_blank" rel="noopener" class="review-badge">\n'
        '          <div class="review-badge-source">Planity</div>\n'
        f'          <div class="review-badge-score">{fr(note_p)}</div>\n'
        f'          <div class="review-badge-stars">{etoiles(note_p)}</div>\n'
        f'          <div class="review-badge-count">{nb_p} avis</div>\n'
        "        </a>\n"
        f'        <a href="{lien_g}" target="_blank" rel="noopener" class="review-badge">\n'
        '          <div class="review-badge-source">Google</div>\n'
        f'          <div class="review-badge-score">{fr(note_g)}</div>\n'
        f'          <div class="review-badge-stars">{etoiles(note_g)}</div>\n'
        f'          <div class="review-badge-count">{nb_g} avis</div>\n'
        "        </a>\n"
        "      </div>"
    )

    # Alternance Planity / Google pour varier les sources dans le carrousel
    cartes = []
    gg = g["avis_google"]
    for i in range(max(len(planity), len(gg))):
        if i < len(planity):
            t, j = planity[i]
            cartes.append(carte(t, "Cliente Planity", f"Planity — {j:%d/%m/%Y}"))
        if i < len(gg):
            cartes.append(carte(gg[i]["texte"], gg[i]["auteur"], "Google"))
    serie = "".join(cartes)
    track = (
        '      <div class="reviews-track">\n' + serie
        + "        <!-- Duplicate set for infinite marquee loop -->\n" + serie
        + "      </div>"
    )

    cta = (
        '    <div class="reviews-cta">\n'
        f'      <a href="{URL_PLANITY}" target="_blank" rel="noopener">Voir les {nb_p} avis Planity &rarr;</a>\n'
        f'      <a href="{lien_g}" target="_blank" rel="noopener">Laisser un avis Google &rarr;</a>\n'
        "    </div>"
    )

    index = RACINE / "index.html"
    s = index.read_text()
    s = remplacer(s, "BADGES", badges)
    s = remplacer(s, "TRACK", track)
    s = remplacer(s, "CTA", cta)
    index.write_text(s)

    citations = "\n".join(f"- « {t} » (Planity, {j:%d/%m/%Y})" for t, j in planity[:5])
    llms_bloc = (
        f"- Planity : {str(note_p).replace('.', ',')}/5 sur {nb_p} avis vérifiés ({URL_PLANITY})\n"
        f"- Google : {fr(note_g)}/5 sur {nb_g} avis\n"
        f"- Derniers avis Planity :\n{citations}\n"
        f"- Avis relevés le {date.today():%d/%m/%Y}\n"
    )
    llms = RACINE / "llms.txt"
    l = remplacer(llms.read_text(), "LLMS", llms_bloc)
    l = re.sub(r"Mis à jour le .*\.", f"Mis à jour le {date.today():%d/%m/%Y}.", l)
    llms.write_text(l)

    print(f"Planity {note_p}/5 ({nb_p} avis), {len(planity)} avis Planity + {len(gg)} Google dans le carrousel.")


if __name__ == "__main__":
    main()
