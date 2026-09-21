# tests/unit/pipeline/test_confiance.py
from __future__ import annotations

from app.pipeline.confiance import Clause, scorer


def test_corroboration_une_seule_section_document_multi_sections():
    clause = Clause(type="résiliation", extrait="...", confiance_llm=0.9, sections=[0])
    clauses, _ = scorer([clause], nb_sections=3)
    assert clauses[0].confiance == 0.0  # n=1, doc multi-sections → corroboration 0


def test_corroboration_deux_sections():
    clause = Clause(type="résiliation", extrait="...", confiance_llm=0.8, sections=[0, 2])
    clauses, _ = scorer([clause], nb_sections=3)
    assert clauses[0].confiance == 0.4  # 0.8 * 0.5


def test_corroboration_trois_sections_ou_plus():
    clause = Clause(type="résiliation", extrait="...", confiance_llm=0.7, sections=[0, 1, 2])
    clauses, _ = scorer([clause], nb_sections=3)
    assert clauses[0].confiance == 0.7  # 0.7 * 1.0


def test_document_une_seule_section_ne_penalise_pas():
    clause = Clause(type="résiliation", extrait="...", confiance_llm=0.9, sections=[0])
    clauses, _ = scorer([clause], nb_sections=1)
    assert clauses[0].confiance == 0.9  # corroboration = 1 (rien à corroborer)


def test_score_global_est_le_minimum():
    a = Clause(type="a", extrait="x", confiance_llm=0.9, sections=[0, 1, 2])
    b = Clause(type="b", extrait="y", confiance_llm=0.9, sections=[0])
    _, score_global = scorer([a, b], nb_sections=3)
    assert score_global == 0.0  # b : 0.9 * 0 = 0, minimum des deux


def test_score_global_zero_sans_clause():
    _, score_global = scorer([], nb_sections=3)
    assert score_global == 0.0
