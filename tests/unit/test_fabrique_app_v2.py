"""Fabrique de rôle : le container `v2` ne sert que /v2 (+ /health).

Le rôle vient de la commande uvicorn (`app.main:create_app_v2 --factory`),
jamais d'une variable d'environnement : une variable perdue dans le `.env`
partagé retirerait `/v1` au service `app` (docs/spec-v2.md §3, v1 jamais
interrompue).

Pas de fixture d'environnement ici : l'autouse `environnement` de
`tests/conftest.py` (MOCK=on, DRIFT=off, LLM_PROVIDER=ollama, LLM_MODEL,
METRICS_PATH et REGISTRY_PATH en tmp_path, OTEL_TRACES=off) s'applique déjà
à tout `tests/`, y compris `tests/unit/`.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app import api_v2
from app.main import create_app, create_app_v2
from app.telemetry import build_telemetry


def _client_v2(tmp_path) -> TestClient:
    """App du rôle v2, télémétrie surchargée pour ne pas écrire dans le vrai
    `ops/metrics.jsonl` (même précaution que `tests/unit/test_api_v2_analyser.py`)."""
    app = create_app_v2()
    app.dependency_overrides[api_v2.get_telemetry] = lambda: build_telemetry(
        span_exporter=InMemorySpanExporter(), metrics_path=tmp_path / "metrics.jsonl", level="INFO"
    )
    return TestClient(app)


def test_create_app_v2_analyse_un_contrat(tmp_path):
    """La route /v2/analyse est bien montée et fonctionnelle dans le rôle v2."""
    texte = "Article 1 — Objet\n\n" + ("Texte du contrat. " * 20)
    r = _client_v2(tmp_path).post("/v2/analyse", json={"texte": texte})
    assert r.status_code == 200
    assert r.json()["version"]


def test_create_app_v2_sans_route_v1(tmp_path):
    """Le contrat v1 n'est pas servi par ce rôle : 404, pas 422 ni 200."""
    r = _client_v2(tmp_path).post("/v1/analyse", json={"texte": "x" * 40})
    assert r.status_code == 404


def test_create_app_v2_sans_route_gateway(tmp_path):
    client = _client_v2(tmp_path)
    assert client.post("/analyse", json={"texte": "x" * 40}).status_code == 404
    assert client.get("/gateway/etat").status_code == 404


def test_create_app_v2_expose_health(tmp_path):
    """Nécessaire au healthcheck du container `v2` (docker-compose.yml)."""
    r = _client_v2(tmp_path).get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_app_conserve_les_trois_routers():
    """Non-régression du service `app` : la fabrique historique est intacte."""
    chemins = {route.path for route in create_app().routes}
    assert {"/v1/analyse", "/v2/analyse", "/analyse", "/gateway/etat", "/health"} <= chemins
