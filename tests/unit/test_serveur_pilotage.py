"""Squelette du serveur de pilotage : les 6 routes du contrat gelé
(`conception_figee/pilotage/openapi-pilotage.json`) répondent 501, et les 3
routes d'écriture valident leur corps AVANT de lever (corps invalide → 422).

Aucune logique métier ici : lecture de `metrics.jsonl`, décisions, écriture
du registre et du journal sont le chantier 2.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from ops.serveur_pilotage import creer_app_pilotage

client = TestClient(creer_app_pilotage())


def test_health_repond_200():
    """Extension hors contrat gelé, nécessaire au healthcheck du container."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_les_six_routes_du_contrat_sont_montees():
    """Garde-fou contre une faute de frappe sur un chemin du contrat gelé."""
    chemins = {route.path for route in creer_app_pilotage().routes}
    assert {
        "/pilotage/dashboard",
        "/pilotage/regles",
        "/pilotage/regles/{signal}",
        "/pilotage/promotion",
        "/pilotage/rollback",
        "/pilotage/journal",
    } <= chemins


def test_dashboard_501():
    r = client.get("/pilotage/dashboard")
    assert r.status_code == 501
    assert "detail" in r.json()


def test_regles_501():
    r = client.get("/pilotage/regles")
    assert r.status_code == 501
    assert "detail" in r.json()


def test_journal_501():
    r = client.get("/pilotage/journal")
    assert r.status_code == 501
    assert "detail" in r.json()


def test_journal_accepte_les_parametres_du_contrat():
    """`signal` et `limite` sont optionnels (limite: défaut 100)."""
    r = client.get("/pilotage/journal", params={"signal": "latence_p95", "limite": 10})
    assert r.status_code == 501


def test_ajuster_seuil_corps_valide_501():
    r = client.put(
        "/pilotage/regles/latence_p95",
        json={"seuil": "> 9 s", "declencheur": "humain"},
    )
    assert r.status_code == 501
    assert "detail" in r.json()


def test_ajuster_seuil_declencheur_hors_enumeration_422():
    r = client.put(
        "/pilotage/regles/latence_p95",
        json={"seuil": "> 9 s", "declencheur": "robot"},
    )
    assert r.status_code == 422


def test_promotion_corps_valide_501():
    r = client.post("/pilotage/promotion", json={"cible_pct": 50, "declencheur": "humain"})
    assert r.status_code == 501
    assert "detail" in r.json()


def test_promotion_palier_hors_enumeration_422():
    """Le contrat gelé n'autorise que les paliers 50 et 100."""
    r = client.post("/pilotage/promotion", json={"cible_pct": 75})
    assert r.status_code == 422


def test_rollback_corps_valide_501():
    r = client.post(
        "/pilotage/rollback",
        json={"declencheur": "auto", "signal": "taux_erreur", "valeur": "12 %"},
    )
    assert r.status_code == 501
    assert "detail" in r.json()


def test_rollback_sans_declencheur_422():
    """`declencheur` est le seul champ requis du schéma gelé `Rollback`."""
    r = client.post("/pilotage/rollback", json={"signal": "taux_erreur"})
    assert r.status_code == 422
