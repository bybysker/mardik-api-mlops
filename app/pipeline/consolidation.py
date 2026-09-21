"""Fusion et dédoublonnage des clauses extraites section par section (*reduce*). [STUB]

Contrat attendu :

    consolider(par_section: list[list[Clause]]) -> list[Clause]

* Deux clauses du même ``type`` trouvées dans des sections différentes sont
  **une seule** clause dans le résultat : on garde l'extrait le plus long (le
  plus informatif), on fusionne les ``sections`` et on retient la
  ``confiance_llm`` maximale déclarée.
* L'ordre de sortie suit l'ordre d'apparition dans le contrat (première
  section où la clause a été vue).
* Le résultat ne contient jamais deux clauses de même type.
"""
from __future__ import annotations

from app.pipeline.confiance import Clause


def consolider(par_section: list[list[Clause]]) -> list[Clause]:
    par_type: dict[str, Clause] = {}
    ordre: list[str] = []
    for clauses_section in par_section:
        for clause in clauses_section:
            existante = par_type.get(clause.type)
            if existante is None:
                par_type[clause.type] = Clause(
                    type=clause.type,
                    extrait=clause.extrait,
                    confiance_llm=clause.confiance_llm,
                    sections=list(clause.sections),
                )
                ordre.append(clause.type)
            else:
                if len(clause.extrait) > len(existante.extrait):
                    existante.extrait = clause.extrait
                existante.confiance_llm = max(existante.confiance_llm, clause.confiance_llm)
                for idx in clause.sections:
                    if idx not in existante.sections:
                        existante.sections.append(idx)
    return [par_type[t] for t in ordre]
