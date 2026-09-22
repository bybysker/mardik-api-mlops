"""Tests unitaires — eval/run_eval.py::evaluer (formule de note = rappel,
garde-fou seuil_note par contrat). Les tests d'acceptance fournis
(tests/acceptance/test_chaine.py) couvrent déjà le chemin heureux sur les
12 contrats ; ces tests ciblent le comportement de garde-fou."""
from __future__ import annotations

import json


def test_passe_faux_si_un_contrat_sous_son_seuil(tmp_path, historique):
    from eval.run_eval import charger_attendus, evaluer

    item = dict(charger_attendus()["c07"])
    item["seuil_note"] = 0.99  # aucune réponse MOCK réaliste n'atteint 99 % de rappel
    chemin_attendus = tmp_path / "attendus.jsonl"
    chemin_attendus.write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")

    rapport = evaluer(
        "v1", seuil=0.1, sous_ensemble=["c07"], attendus=chemin_attendus, historique=historique
    )

    assert rapport.par_contrat["c07"]["seuil_note"] == 0.99
    assert rapport.passe is False
    assert any("c07" in motif for motif in rapport.motifs)


def test_historique_recoit_une_ligne_par_appel(historique):
    from eval.run_eval import evaluer

    evaluer("v1", sous_ensemble=["c01"], historique=historique)
    evaluer("v1", sous_ensemble=["c01"], historique=historique)

    lignes = historique.read_text(encoding="utf-8").strip().splitlines()
    assert len(lignes) == 2
    assert json.loads(lignes[0])["version"] == "v1.0.0"
