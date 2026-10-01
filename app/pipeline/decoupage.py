"""Découpage d'un contrat par clauses (étape *map* du map-reduce).

Contrat :

    decouper(texte: str, taille_max: int = 6000) -> list[Section]

* Une ``Section`` porte un ``titre`` (l'intitulé de l'article, ou ``"préambule"``),
  un ``texte`` et son ``indice`` (ordre dans le contrat).
* Le découpage suit les intitulés d'articles (« Article 3 — Résiliation »,
  « 3. Résiliation », « ARTICLE 3 : … »). Une section plus longue que
  ``taille_max`` est elle-même découpée en morceaux, sans couper une phrase.
* La concaténation des ``texte`` de toutes les sections doit couvrir tout le
  contrat : rien ne doit être perdu — c'est précisément ce que la v1 ne
  garantit pas.

Trois niveaux de découpage :
1. découpage structurel (articles/préambule/annexes) ;
2. regroupement des blocs consécutifs jusqu'à ``taille_max`` (repli
   « paragraphes » : limite le nombre d'appels LLM) ;
3. repli taille fixe avec chevauchement pour un bloc qui dépasse
   ``taille_max`` à lui seul.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MOTIF_TITRE = re.compile(
    r"^(Article\s+\d+\s*[—:-].*|Pr[ée]ambule\s*$|Annexe\s+\d+.*|Chapitre\s+.*|"
    r"Titre\s+[IVXLCDM]+.*)$",
    re.IGNORECASE | re.MULTILINE,
)
CHEVAUCHEMENT = 250


@dataclass
class Section:
    indice: int
    titre: str
    texte: str


def decouper(texte: str, taille_max: int = 6000) -> list[Section]:
    limites: list[tuple[int, str]] = []
    for m in MOTIF_TITRE.finditer(texte):
        titre = m.group(0).strip()
        if titre.lower() == "préambule":
            titre = "préambule"  # normalisé, quelle que soit la casse source
        limites.append((m.start(), titre))

    blocs: list[tuple[str, str]] = []
    debut_premier = limites[0][0] if limites else len(texte)
    preambule = texte[:debut_premier].strip()
    if preambule:
        blocs.append(("préambule", preambule))

    for i, (pos, titre) in enumerate(limites):
        fin = limites[i + 1][0] if i + 1 < len(limites) else len(texte)
        corps = texte[pos:fin].strip()
        if corps:
            blocs.append((titre, corps))

    groupes = _regrouper(blocs, taille_max)

    resultat: list[Section] = []
    indice = 0
    for titres, corps in groupes:
        for morceau in _decouper_taille(corps, taille_max):
            resultat.append(Section(indice=indice, titre=" ; ".join(titres), texte=morceau))
            indice += 1
    return resultat


def _regrouper(blocs: list[tuple[str, str]], taille_max: int) -> list[tuple[list[str], str]]:
    """Accumule les blocs consécutifs jusqu'à ~taille_max (repli « paragraphes »
    de decoupage-chunking.md : limite le nombre d'appels LLM, pas un cas rare)."""
    groupes: list[tuple[list[str], str]] = []
    titres_courants: list[str] = []
    texte_courant = ""
    for titre, corps in blocs:
        candidat = f"{texte_courant}\n\n{corps}".strip() if texte_courant else corps
        if texte_courant and len(candidat) > taille_max:
            groupes.append((titres_courants, texte_courant))
            titres_courants = [titre]
            texte_courant = corps
        else:
            titres_courants.append(titre)
            texte_courant = candidat
    if texte_courant:
        groupes.append((titres_courants, texte_courant))
    return groupes


def _decouper_taille(texte: str, taille_max: int) -> list[str]:
    if len(texte) <= taille_max:
        return [texte]
    morceaux: list[str] = []
    debut = 0
    while debut < len(texte):
        fin = min(debut + taille_max, len(texte))
        if fin < len(texte):
            fin_phrase = texte.rfind(". ", debut, fin)
            if fin_phrase > debut:
                fin = fin_phrase + 1
        morceau = texte[debut:fin].strip()
        if morceau:
            morceaux.append(morceau)
        if fin >= len(texte):
            break
        debut = max(debut + 1, fin - CHEVAUCHEMENT)  # garantit une progression (pas de boucle infinie)
    return morceaux
