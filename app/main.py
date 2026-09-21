"""Application FastAPI — [FOURNI], étendu (fabrique de rôle, 2026-09-21).

* ``/v1`` est branché et fonctionnel (le contrat historique) ;
* ``/v2`` et ``/analyse`` (gateway) sont branchés sur des stubs : tant qu'un
  module lève ``NotImplementedError``, la route répond **501** avec le nom du
  chantier restant — jamais un 500 muet.

Deux fabriques, un seul artefact (``docs/spec-v2.md`` §4) :

* ``create_app()`` — rôle complet, service ``app`` du compose (port 8000) ;
* ``create_app_v2()`` — rôle « v2 », service ``v2`` du compose (port 8001).

Le rôle est choisi par la **commande uvicorn**, jamais par une variable
d'environnement : le ``.env`` est partagé par tous les services du compose,
une variable de rôle qui s'y glisserait retirerait ``/v1`` au service ``app``.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from app import api_v1, api_v2, gateway
from app.telemetry import build_default_telemetry


def _creer(*, titre: str, routers: tuple[APIRouter, ...]) -> FastAPI:
    """Partie commune à tous les rôles : télémétrie, routers, /health, 501."""
    app = FastAPI(title=titre, version="2.0.0")
    build_default_telemetry()

    for router in routers:
        app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "provider": os.environ.get("LLM_PROVIDER", "ollama"),
            "mock": os.environ.get("MOCK", "off"),
        }

    @app.exception_handler(NotImplementedError)
    async def _non_implemente(request: Request, exc: NotImplementedError) -> JSONResponse:
        return JSONResponse(
            status_code=501,
            content={"detail": f"à implémenter : {exc or 'module non implémenté'}"},
        )

    return app


def create_app() -> FastAPI:
    """Rôle complet : ``/v1``, ``/v2`` et la gateway (service ``app``)."""
    return _creer(
        titre="Mardik — analyse de contrats",
        routers=(api_v1.router, api_v2.router, gateway.router),
    )


def create_app_v2() -> FastAPI:
    """Rôle « v2 » : ``/v2`` seulement (service ``v2``, port hôte 8001)."""
    return _creer(
        titre="Mardik — analyse de contrats (rôle v2)",
        routers=(api_v2.router,),
    )


app = create_app()
