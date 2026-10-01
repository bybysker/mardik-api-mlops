# tests/unit/pipeline/test_decoupage.py
from __future__ import annotations

from app.pipeline.decoupage import decouper


def test_regroupe_articles_courts_pour_limiter_les_appels():
    """Plusieurs articles courts tiennent dans une seule section groupée."""
    texte = (
        "Article 1 — Objet\n\nTexte court.\n\n"
        "Article 2 — Durée\n\nTexte court aussi.\n\n"
        "Article 3 — Prix\n\nEncore un texte court.\n"
    )
    sections = decouper(texte, taille_max=6000)
    assert len(sections) == 1
    assert "Article 1 — Objet" in sections[0].titre
    assert "Article 3 — Prix" in sections[0].titre
    assert "Texte court aussi" in sections[0].texte


def test_decoupe_par_article_sans_regroupement_si_gros():
    """Chaque article, seul, tient sous taille_max (pas de repli taille fixe
    déclenché) mais deux articles combinés le dépassent (pas de regroupement
    entre eux). Tailles vérifiées : ~450-480 car. par bloc, taille_max=800 —
    marge large dans les deux sens (bloc seul < 800, deux blocs > 800)."""
    texte = (
        "Préambule\n\n" + ("Contexte du contrat détaillé. " * 15) + "\n\n"
        "Article 1 — Objet\n\n" + ("Objet du contrat détaillé. " * 15) + "\n\n"
        "Article 2 — Durée\n\n" + ("Durée du contrat détaillée. " * 15) + "\n"
    )
    sections = decouper(texte, taille_max=800)
    titres = [s.titre for s in sections]
    assert titres == ["préambule", "Article 1 — Objet", "Article 2 — Durée"]


def test_couvre_tout_le_texte_sans_perte():
    remplissage = "Remplissage. " * 2000
    texte = (
        f"Article 1 — Objet\n\nPremière phrase. {remplissage}\n\n"
        "Article 2 — Fin\n\nDernière phrase avec résiliation.\n"
    )
    sections = decouper(texte, taille_max=6000)
    reconstitue = "".join(s.texte for s in sections)
    assert "Première phrase" in reconstitue
    assert "résiliation" in reconstitue
    assert len(sections) > 1  # le remplissage dépasse largement taille_max


def test_section_trop_longue_est_redecoupee_avec_chevauchement():
    long_texte = "Article 1 — Long\n\n" + "".join(f"Phrase numéro {i}. " for i in range(1000))
    sections = decouper(long_texte, taille_max=1000)
    morceaux_article_1 = [s for s in sections if s.titre == "Article 1 — Long"]
    assert len(morceaux_article_1) > 1
    for s in morceaux_article_1:
        assert len(s.texte) <= 1000 + 260  # taille_max + marge de chevauchement
    # chevauchement réel : la fin du 1er morceau réapparaît au début du 2e
    fin_premier = morceaux_article_1[0].texte[-100:]
    assert any(fin_premier[-30:] in m.texte for m in morceaux_article_1[1:])


def test_indices_croissants():
    texte = "Article 1 — A\n\ntexte a.\n\nArticle 2 — B\n\ntexte b.\n"
    sections = decouper(texte)
    assert [s.indice for s in sections] == list(range(len(sections)))


def test_pas_de_titre_devient_preambule():
    texte = "Juste un paragraphe sans titre d'article, assez court."
    sections = decouper(texte)
    assert len(sections) == 1
    assert sections[0].titre == "préambule"


def test_preambule_explicite_normalise_en_minuscule():
    """Un en-tête « Préambule » (majuscule) explicite est normalisé, comme le cas implicite."""
    texte = "Préambule\n\nLe client souhaite un service.\n"
    sections = decouper(texte)
    assert sections[0].titre == "préambule"
