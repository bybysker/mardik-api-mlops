# tests/unit/test_bundle_v2.py
from __future__ import annotations

from app.llm_client import Bundle


def test_bundle_v2_strategie_map_reduce():
    bundle = Bundle.charger("v2")
    assert bundle.strategie == "map_reduce_clauses"


def test_bundle_v2_schema_sortie_defini():
    bundle = Bundle.charger("v2")
    assert bundle.schema_sortie
    assert "clauses" in bundle.schema_sortie["properties"]


def test_bundle_v2_taille_section():
    bundle = Bundle.charger("v2")
    assert bundle.parametres["contexte_max_caracteres"] == 6000
