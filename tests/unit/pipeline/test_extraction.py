from __future__ import annotations

import pytest

from app.llm_client import Bundle, LLMClient
from app.pipeline.decoupage import Section
from app.pipeline.extraction import extraire


@pytest.fixture
def client_v2(monkeypatch: pytest.MonkeyPatch, tmp_path) -> LLMClient:
    monkeypatch.setenv("MOCK", "on")
    # dossier de fixtures vide et isolé : le test dépend du repli par mots-clés
    # (reponse_de_repli), jamais d'une vraie fixture enregistrée par `make fixtures`
    return LLMClient(Bundle.charger("v2"), fixtures=tmp_path / "fixtures_vides")


def test_extrait_une_clause_via_mots_cles(client_v2: LLMClient):
    section = Section(
        indice=0,
        titre="Article 1 — Résiliation",
        texte="En cas de résiliation anticipée, un préavis de deux mois est requis.",
    )
    clauses, reponse = extraire(section, client_v2)
    assert any(c.type == "résiliation" for c in clauses)
    assert all(c.sections == [0] for c in clauses)
    assert reponse.mock is True


def test_section_sans_clause_renvoie_liste_vide(client_v2: LLMClient):
    section = Section(indice=1, titre="Article 2", texte="Texte neutre sans mot-clé connu.")
    clauses, _ = extraire(section, client_v2)
    assert clauses == []


def test_confiance_hors_bornes_est_ignoree(client_v2: LLMClient, monkeypatch: pytest.MonkeyPatch):
    from app.llm_client import ReponseLLM

    def fausse_reponse(*_args, **_kwargs):
        return ReponseLLM(
            texte='{"clauses": [{"type": "résiliation", "extrait": "x", "confiance": 1.7}]}',
            latence_ms=1.0,
            mock=True,
        )

    monkeypatch.setattr(client_v2, "completer", fausse_reponse)
    section = Section(indice=0, titre="A", texte="peu importe")
    clauses, _ = extraire(section, client_v2)
    assert clauses == []


def test_json_invalide_ne_plante_pas(client_v2: LLMClient, monkeypatch: pytest.MonkeyPatch):
    from app.llm_client import ReponseLLM

    def fausse_reponse(*_args, **_kwargs):
        return ReponseLLM(texte="pas du json", latence_ms=1.0, mock=True)

    monkeypatch.setattr(client_v2, "completer", fausse_reponse)
    section = Section(indice=0, titre="A", texte="peu importe")
    clauses, reponse = extraire(section, client_v2)
    assert clauses == []
    assert reponse.texte == "pas du json"
