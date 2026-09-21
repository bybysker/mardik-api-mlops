"""Serveur de pilotage — SQUELETTE (chantier 2).

Contrat gelé : ``conception_figee/pilotage/openapi-pilotage.json``. Ce module
monte les 6 routes du contrat et **rien d'autre** ; chaque route valide son
entrée (modèles Pydantic repris du contrat) puis lève ``NotImplementedError``,
traduit en 501 par le handler — jamais un 500 muet, même mécanisme que
``app/main.py``.

Un corps de requête invalide est donc refusé en **422** avant d'atteindre le
handler ; un corps valide obtient **501**. C'est volontaire : le contrat est
respecté dès le squelette.

À ce stade le module **ne lit ni n'écrit aucun fichier** : la lecture de
``ops/metrics.jsonl``, les décisions, l'écriture du registre et du journal de
pilotage, la régénération du Caddyfile sont le chantier 2.

Lancement : ``uvicorn ops.serveur_pilotage:app --host 0.0.0.0 --port 8000``
(service ``serveur_pilotage`` du docker-compose, port hôte 8002).
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/pilotage", tags=["pilotage"])


class AjustementSeuil(BaseModel):
    """Corps de ``PUT /pilotage/regles/{signal}`` — schéma gelé ``AjustementSeuil``."""

    seuil: str
    declencheur: Literal["auto", "humain"]


class Promotion(BaseModel):
    """Corps de ``POST /pilotage/promotion`` — schéma gelé ``Promotion``.

    ``cible_pct`` est le palier canary suivant : 10 → 50 → 100 %, donc seuls
    50 et 100 sont demandables."""

    cible_pct: Literal[50, 100]
    declencheur: Literal["auto", "humain"] | None = None


class Rollback(BaseModel):
    """Corps de ``POST /pilotage/rollback`` — schéma gelé ``Rollback``.

    ``signal`` et ``valeur`` documentent la cause quand le rollback est
    automatique ; le contrat ne les rend pas obligatoires."""

    declencheur: Literal["auto", "humain"]
    signal: str | None = None
    valeur: str | None = None


@router.get("/dashboard")
def lire_dashboard() -> dict[str, Any]:
    raise NotImplementedError("pilotage.lire_dashboard — GET /pilotage/dashboard")


@router.get("/regles")
def lire_regles() -> dict[str, Any]:
    raise NotImplementedError("pilotage.lire_regles — GET /pilotage/regles")


@router.put("/regles/{signal}")
def ajuster_seuil(signal: str, ajustement: AjustementSeuil) -> dict[str, Any]:
    raise NotImplementedError("pilotage.ajuster_seuil — PUT /pilotage/regles/{signal}")


@router.post("/promotion")
def promouvoir(promotion: Promotion) -> dict[str, Any]:
    raise NotImplementedError("pilotage.promouvoir — POST /pilotage/promotion")


@router.post("/rollback")
def rollback(demande: Rollback) -> dict[str, Any]:
    raise NotImplementedError("pilotage.rollback — POST /pilotage/rollback")


@router.get("/journal")
def lire_journal(signal: str | None = None, limite: int = 100) -> dict[str, Any]:
    raise NotImplementedError("pilotage.lire_journal — GET /pilotage/journal")


def creer_app_pilotage() -> FastAPI:
    app = FastAPI(title="Mardik — serveur de pilotage", version="1.0.0")
    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Hors contrat gelé, non normative : sert le healthcheck du container."""
        return {"status": "ok", "role": "pilotage"}

    @app.exception_handler(NotImplementedError)
    async def _non_implemente(request: Request, exc: NotImplementedError) -> JSONResponse:
        return JSONResponse(
            status_code=501,
            content={"detail": f"à implémenter : {exc or 'module non implémenté'}"},
        )

    return app


app = creer_app_pilotage()
