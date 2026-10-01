from __future__ import annotations

from app.pipeline.confiance import Clause
from app.pipeline.consolidation import consolider


def test_fusionne_meme_type_plusieurs_sections():
    par_section = [
        [Clause(type="résiliation", extrait="courte", confiance_llm=0.7, sections=[0])],
        [Clause(type="résiliation", extrait="un extrait plus long et complet", confiance_llm=0.9, sections=[1])],
    ]
    resultat = consolider(par_section)
    assert len(resultat) == 1
    assert resultat[0].extrait == "un extrait plus long et complet"
    assert resultat[0].confiance_llm == 0.9
    assert resultat[0].sections == [0, 1]


def test_aucun_doublon_de_type():
    par_section = [
        [Clause(type="durée", extrait="a", confiance_llm=0.5, sections=[0])],
        [Clause(type="durée", extrait="b", confiance_llm=0.6, sections=[1])],
        [Clause(type="durée", extrait="c", confiance_llm=0.4, sections=[2])],
    ]
    resultat = consolider(par_section)
    types = [c.type for c in resultat]
    assert len(types) == len(set(types))


def test_ordre_premiere_apparition():
    par_section = [
        [Clause(type="prix et paiement", extrait="a", confiance_llm=0.5, sections=[0])],
        [Clause(type="résiliation", extrait="b", confiance_llm=0.5, sections=[1])],
    ]
    resultat = consolider(par_section)
    assert [c.type for c in resultat] == ["prix et paiement", "résiliation"]


def test_sections_vides_ne_cassent_rien():
    assert consolider([[], []]) == []
