"""Tests unitaires — ops/deploy.py (publier/canary/promotion/rollback,
sans app/gateway.py ni surveiller, hors périmètre du point 3)."""
from __future__ import annotations

import pytest


def test_prochaine_version_patch_par_defaut(registry):
    from ops.deploy import prochaine_version

    assert prochaine_version(registry=registry) == "v1.0.1"


def test_prochaine_version_minor(registry):
    from ops.deploy import prochaine_version

    assert prochaine_version("minor", registry=registry) == "v1.1.0"


def test_prochaine_version_major(registry):
    from ops.deploy import prochaine_version

    assert prochaine_version("major", registry=registry) == "v2.0.0"


def test_prochaine_version_bump_invalide(registry):
    from ops.deploy import prochaine_version

    with pytest.raises(ValueError):
        prochaine_version("oups", registry=registry)


from app.llm_client import Bundle


def _livrer_v2(registry, version="v2.0.0"):
    registry.etiqueter(version, Bundle.charger("v2"), commit="abc1234", note_eval=0.9)
    return version


def test_deployer_canary_pourcentage_par_defaut(registry):
    from ops.deploy import deployer_canary

    _livrer_v2(registry)
    index = deployer_canary("v2.0.0", registry=registry)

    assert index["canary"] == "v2.0.0"
    assert index["canary_percent"] == 10  # CANARY_PERCENT non défini dans les tests -> défaut 10
    assert index["active"] == "v1.0.0"
    assert registry.journal()[-1] == {
        **registry.journal()[-1],
        "evenement": "canary",
        "version": "v2.0.0",
        "pourcentage": 10,
    }


def test_deployer_canary_pourcentage_explicite(registry):
    from ops.deploy import deployer_canary

    _livrer_v2(registry)
    index = deployer_canary("v2.0.0", pourcentage=30, registry=registry)

    assert index["canary"] == "v2.0.0" and index["canary_percent"] == 30


def test_promouvoir(registry):
    from ops.deploy import promouvoir

    _livrer_v2(registry)
    index = promouvoir("v2.0.0", registry=registry)

    assert index["active"] == "v2.0.0"
    assert index["precedente"] == "v1.0.0"
    assert index["canary"] is None and index["canary_percent"] == 0
    assert registry.journal()[-1]["evenement"] == "promotion"


def test_rollback_sans_canary_en_cours(registry):
    from ops.deploy import promouvoir, rollback

    _livrer_v2(registry)
    promouvoir("v2.0.0", registry=registry)

    index = rollback(registry=registry, motif="test")

    assert index["active"] == "v1.0.0"
    assert index["precedente"] == "v2.0.0"
    assert index["canary"] is None
    assert registry.journal()[-1]["evenement"] == "rollback"
    assert registry.journal()[-1]["motif"] == "test"


def test_rollback_avec_canary_en_cours(registry):
    from ops.deploy import deployer_canary, rollback

    _livrer_v2(registry)
    deployer_canary("v2.0.0", pourcentage=20, registry=registry)

    index = rollback(registry=registry)

    assert index["active"] == "v1.0.0"  # inchangé : aucune promotion n'a eu lieu
    assert index["canary"] is None and index["canary_percent"] == 0
