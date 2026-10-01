"""Extraction des clauses d'une section (un appel LLM, sortie JSON contrainte).

Contrat :

    extraire(section: Section, client: LLMClient) -> tuple[list[Clause], ReponseLLM]

* Un appel ``client.completer(..., json_mode=True)`` par section : le prompt
  système vient du bundle v2, le prompt utilisateur contient le titre et le
  texte de la section.
* La réponse est parsée selon ``bundle.schema_sortie`` ; une réponse qui ne
  respecte pas le schéma (JSON invalide, champ manquant, type inconnu,
  confiance hors [0, 1]) ne doit pas faire planter l'analyse : la clause
  fautive est ignorée et l'incident est signalé par un log d'avertissement
  (``logging``, voir plus bas — ``extraire()`` n'a pas accès à la télémétrie
  du module ``app.telemetry``). Le nombre de clauses effectivement retenues
  par appel est en outre visible côté orchestration via l'attribut
  ``llm.clauses`` du span ``llm.appel`` (``app/api_v2.py``).
* Chaque ``Clause`` renvoyée porte ``sections=[section.indice]`` et
  ``confiance_llm`` = la valeur déclarée par le modèle ; le score composite
  est calculé plus tard (``confiance.py``).
* La ``ReponseLLM`` est renvoyée telle quelle pour que l'appelant puisse
  agréger latence, tokens et coût.

Indices : ``app.llm_client.TYPES_CLAUSES`` liste les types valides ;
``ReponseLLM.json()`` extrait le JSON d'une réponse (et lève ``ErreurLLM`` sinon).
"""
from __future__ import annotations

import logging

from app.llm_client import ErreurLLM, LLMClient, ReponseLLM, TYPES_CLAUSES
from app.pipeline.confiance import Clause
from app.pipeline.decoupage import Section

logger = logging.getLogger(__name__)


def extraire(section: Section, client: LLMClient) -> tuple[list[Clause], ReponseLLM]:
    prompt_utilisateur = f"{section.titre}\n\n{section.texte}"
    reponse = client.completer(prompt_utilisateur, json_mode=True)

    clauses: list[Clause] = []
    try:
        data = reponse.json()
    except ErreurLLM:
        logger.warning("extraction: réponse LLM non JSON, section %s ignorée", section.indice)
        return clauses, reponse

    brutes = data.get("clauses", []) if isinstance(data, dict) else []
    types_connus = set(TYPES_CLAUSES)
    for item in brutes:
        if not isinstance(item, dict):
            logger.warning("extraction: item de clause non-objet ignoré, section %s", section.indice)
            continue
        type_ = item.get("type")
        extrait = item.get("extrait")
        confiance = item.get("confiance")
        if type_ not in types_connus:
            logger.warning("extraction: type de clause inconnu %r ignoré, section %s", type_, section.indice)
            continue
        if not isinstance(extrait, str) or not extrait.strip():
            logger.warning("extraction: extrait invalide ignoré, section %s, type %s", section.indice, type_)
            continue
        if not isinstance(confiance, (int, float)) or not (0.0 <= confiance <= 1.0):
            logger.warning(
                "extraction: confiance hors bornes (%r) ignorée, section %s, type %s",
                confiance, section.indice, type_,
            )
            continue
        clauses.append(
            Clause(type=type_, extrait=extrait.strip(), confiance_llm=float(confiance), sections=[section.indice])
        )
    return clauses, reponse
