from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import api_v2
from app.api_v2 import analyser_v2
from app.llm_client import Bundle, LLMClient
from app.main import create_app
from app.telemetry import Telemetry, build_telemetry
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Pas de fixture d'environnement ici : l'autouse `environnement` de
# `tests/conftest.py` (MOCK=on, DRIFT=off, LLM_PROVIDER=ollama, LLM_MODEL,
# OTEL_TRACES=off) s'applique déjà à tout `tests/`, y compris `tests/unit/`.


@pytest.fixture
def telemetry(tmp_path) -> Telemetry:
    return build_telemetry(
        span_exporter=InMemorySpanExporter(), metrics_path=tmp_path / "metrics.jsonl", level="INFO"
    )


def test_analyser_v2_sur_contrat_multi_articles(telemetry: Telemetry, tmp_path):
    """Chaque article est assez long pour ne pas tenir dans une seule section
    groupée (taille_max=6000 du bundle v2) : vérifie le multi-appels + la
    consolidation, sans dépendre du nombre exact de sections produites par le
    regroupement (Task 2) — seulement qu'il y en a plus d'une."""
    client = LLMClient(Bundle.charger("v2"), fixtures=tmp_path / "fixtures_vides")
    remplissage = "Contexte additionnel du contrat. " * 150  # ~5 000 car.
    texte = (
        f"Préambule\n\n{remplissage}\n\n"
        f"Article 1 — Confidentialité\n\nLes parties respectent la confidentialité "
        f"des informations. {remplissage}\n\n"
        f"Article 2 — Résiliation\n\nLe contrat peut être résilié moyennant préavis. {remplissage}\n"
    )
    resultat = analyser_v2(texte, client, telemetry)
    assert resultat.sections >= 2
    assert resultat.appels_llm == resultat.sections
    types = {c.type for c in resultat.clauses}
    assert {"confidentialité", "résiliation"} <= types
    assert 0.0 <= resultat.confiance_globale <= 1.0
    assert len(resultat.clauses) == len({c.type for c in resultat.clauses})


def test_route_v2_document_trop_long_413(tmp_path):
    app = create_app()
    # Le garde-fou 413 vit désormais dans `analyser_v2` (Important #4) : il
    # enregistre une `Mesure` d'erreur avant de lever, donc la télémétrie par
    # défaut (qui écrirait dans le vrai `ops/metrics.jsonl`) est surchargée
    # ici, comme pour le test « sous la limite » ci-dessous.
    app.dependency_overrides[api_v2.get_telemetry] = lambda: build_telemetry(
        span_exporter=InMemorySpanExporter(), metrics_path=tmp_path / "metrics.jsonl", level="INFO"
    )
    client_http = TestClient(app)
    texte_trop_long = "x" * 250_001
    r = client_http.post("/v2/analyse", json={"texte": texte_trop_long})
    assert r.status_code == 413
    assert "detail" in r.json()


def test_analyser_v2_document_trop_long_leve_exception_hors_http(telemetry: Telemetry, tmp_path):
    """Le garde-fou 413 protège aussi les appelants directs (futur gateway),
    pas seulement la route HTTP — voir `analyser_v2`."""
    client = LLMClient(Bundle.charger("v2"), fixtures=tmp_path / "fixtures_vides")
    texte_trop_long = "x" * 250_001
    with pytest.raises(api_v2.DocumentTropLong):
        analyser_v2(texte_trop_long, client, telemetry)


def test_route_v2_document_sous_la_limite_ne_declenche_pas_413(tmp_path):
    app = create_app()
    app.dependency_overrides[api_v2.get_telemetry] = lambda: build_telemetry(
        span_exporter=InMemorySpanExporter(), metrics_path=tmp_path / "metrics.jsonl", level="INFO"
    )
    client_http = TestClient(app)
    texte = "Article 1 — Objet\n\n" + ("Texte du contrat. " * 20)
    r = client_http.post("/v2/analyse", json={"texte": texte})
    assert r.status_code == 200
