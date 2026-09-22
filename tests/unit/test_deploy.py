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
