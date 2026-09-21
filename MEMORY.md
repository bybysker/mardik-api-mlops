# MEMORY — Contexte projet condensé (mardik-api-mlops)

> Continuité inter-sessions / inter-agents. À mettre à jour à chaque évolution
> significative. Lire ce fichier en premier.

## Projet

**Mardik v2** — outil d'analyse de contrats (lab phase 4, formation dev IA
agentique). Objectif : livrer la v2 (contrats longs sans troncature, score de
confiance) via une chaîne LLMOps automatisée, sans jamais casser la v1.
Contexte : un déploiement manuel raté a motivé la note du CTO « Plus jamais
ça ».

Ce dépôt (`mardik-api-mlops`) est le **code source de départ du brief**
(squelette + stubs + tests d'acceptance fournis), distinct du dossier de
conception qui a précédé son obtention.

## ⚠️ Le dossier de conception est gelé — ne jamais y écrire

`../conception_figee/` (dans le dépôt parent `mardik_nouvelle_version`) est
le dossier de conception produit **avant** d'avoir accès à ce code source. Il
a été présenté (dossier de conception soutenu), puis **gelé volontairement
par l'utilisateur le 2026-09-21** :

- renommé `conception/` → `conception_figee/` ;
- permissions **555** (lecture seule) ;
- le `.git` du dépôt parent `mardik_nouvelle_version` a été **supprimé
  intentionnellement** (pas de remote, donc pas d'historique à récupérer —
  assumé par l'utilisateur).

**Règle stricte : ne plus jamais créer ni modifier de fichier en dehors de
`mardik-api-mlops/`.** Toujours lire `conception_figee/` pour comprendre une
décision passée, jamais y écrire (de toute façon interdit par les
permissions). Un écart découvert entre une décision de conception et le code
réel se documente dans `docs/conception_revue/` (voir plus bas), jamais en
éditant `conception_figee/`.

## Documents de référence (ordre de lecture)

1. `README.md` — structure du dépôt, chantiers, commandes (`make ...`)
2. `docs/besoin_client.md` — expression de besoin (identique au brief connu)
3. `docs/schema_remediation.md` — ce que la remédiation a déjà instrumenté
   (télémétrie v1, à réutiliser tel quel)
4. `docs/analyse-coherence-conception.md` — confrontation entre les décisions
   de `conception_figee/` et le code réel fourni ici : ce qui est cohérent,
   ce qui a dû être révisé
5. `docs/conception_revue/` — versions **révisées** des documents de
   conception dont une décision a dû changer face au code réel (voir
   ci-dessous)
6. `docs/img/pipeline-v1_reel.drawio` / `.png` — pipeline `/v1/analyse` tel
   qu'implémenté (réel)
7. `docs/img/pipeline-v2.drawio` / `.png` — pipeline `/v2/analyse` **cible**
   (pas encore implémenté, tiré des docstrings des stubs)
8. `../conception_figee/` — dossier de conception d'origine, gelé, lecture
   seule, fait foi pour tout ce qui n'a pas été explicitement révisé

## Décisions acquises (héritées de `conception_figee/`, toujours valables)

- **V1 figée** : `/v1/analyse` intouchable (confirmé dans le code réel,
  `app/api_v1.py`), le client `scripts/client_v1.py` doit continuer de
  fonctionner à l'identique.
- **Cause du défaut v1** : troncature explicite à `contexte_max_caracteres`
  (16 000 car.) dans `models/v1/config.yaml`, appliquée **avant** l'appel LLM
  — confirmé dans `app/api_v1.py::analyser_v1`.
- **Contraintes client** : P95 < 8 s (même longs), coût < 0,15 €/analyse,
  ~400 contrats/mois (~13/jour), aucune interruption, rollback immédiat.
- **Jeu d'éval** : 12 contrats (9 courts + 3 longs), seuils 0,75 (courts) /
  0,80 (longs), note = micro-F1 (voir nuance ci-dessous).
- **Score de confiance** : confiance LLM × corroboration (stabilité
  inter-chunks), global = minimum des clauses.
- **Découpage v2** : structurel (articles), taille cible 6 000 car. —
  confirmé par `models/v2/config.yaml::contexte_max_caracteres`.
- **Versionnage** : SemVer, patch auto-incrémenté **au build validé**
  (gate d'éval passé), jamais à la fusion — confirmé par
  `ops/deploy.py::publier` (rejoue le gate, refuse si échec, étiquette
  ensuite).
- **Canary** : paliers 10→50→100 %, critères v2 jamais moins bonne sur
  latence/erreurs/coût + strictement meilleure sur au moins un des trois.
- **Gel avant fusion (chantier 1)** : branche `dev`, deux tags protégés
  auto-posés (`revue-ok/<sha>`, `eval-ok/<sha>`) accumulés sur le même SHA
  figé, fusion `dev → main` en fast-forward strict seulement si les deux
  tags sont présents. `main` ne rejoue aucun gate. Détail complet dans
  `conception_figee/chantier1_llmops/gel-eval-avant-fusion.md` — **pas
  encore traduit en `.github/workflows/llmops.yml` réel** (le fichier fourni
  est un `[TEMPLATE]` générique, à réécrire).

## Écart révisé — fenêtre glissante (comptage → temporelle)

`conception_figee/pilotage/fenetre-glissante-seuils.md` avait décidé une
fenêtre **en nombre de requêtes** (50, min 30). Les tests d'acceptance
**fournis et figés** (`tests/acceptance/test_observabilite.py`) imposent une
interface **temporelle** (`fenetre_s`) sur `ops.deploy.surveiller` et
`ops.dashboard.resume`. Décision (2026-09-21) : garder les tests tels quels,
réviser la conception plutôt que les tests. Détail complet et valeurs
retenues (120 s / 300 s / minimum 10) :
[`docs/conception_revue/pilotage/fenetre-glissante-seuils.md`](docs/conception_revue/pilotage/fenetre-glissante-seuils.md).
Répercussions déjà révisées : `canary.md`, `tableau-pilotage.md` (+ PDF),
`questions_reponses.md` (Q9/Q10/Q12/Q14) — tous dans
`docs/conception_revue/`.

## Points mineurs sans action (voir `docs/analyse-coherence-conception.md`)

- `eval/run_eval.py` (stub) décrit la note comme un « rappel » (recall), la
  conception avait décidé un micro-F1 scindé courts/longs — pas de test qui
  verrouille la formule exacte, le split reste implémentable via le champ
  `seuil_note` par contrat.
- `.github/workflows/llmops.yml` fourni n'est qu'un squelette `[TEMPLATE]`
  (push `main`/PR/tags, pas de branche `dev`) — à réécrire entièrement pour
  refléter le mécanisme à deux tags.
- `app/api_v2.py` (stub) ne documente que 422/503, pas de 413 pour un
  document trop long — ajoutable sans conflit avec les tests fournis.

## État de l'implémentation (2026-09-21)

**Rien n'est encore implémenté.** Tous les fichiers `[STUB]` du README lèvent
`NotImplementedError` : `app/api_v2.py::analyser_v2`, tout `app/pipeline/*`,
`app/gateway.py`, `eval/run_eval.py::evaluer`, `ops/deploy.py::*`,
`ops/dashboard.py::*`. Seuls `app/api_v1.py`, `app/llm_client.py`,
`app/telemetry.py`, `ops/drift_proxy.py`, `ops/registry/` sont `[FOURNI]`
et fonctionnels.

Deux schémas ont été produits pour documenter, sans encore coder :

- le pipeline `/v1/analyse` **réel** (`docs/img/pipeline-v1_reel.drawio`) :
  tout est dans `app/api_v1.py`, seul l'appel LLM est délégué à
  `app/llm_client.py`.
- le pipeline `/v2/analyse` **cible** (`docs/img/pipeline-v2.drawio`) :
  `decoupage → extraction (map, 1 appel LLM/section) → consolidation
  (reduce) → confiance`, orchestré par `app/api_v2.py`.

## Environnement technique

- Dépôt git propre à `mardik-api-mlops`, remote `origin` =
  `git@github.com:wawawaformation/mardik-api-mlops.git` (rien poussé pour
  l'instant).
- `uv` pour les dépendances Python, `make` pour les commandes courantes
  (`make test`, `make eval`, `make ci`, voir `README.md`).
- MOCK=on réservé à la CI (rejoue `eval/fixtures/`), `DRIFT=` pour simuler
  une dérive via `ops/drift_proxy.py`.
- **Fournisseur LLM = Azure AI Inference** (`LLM_PROVIDER=azure`,
  `LLM_MODEL=gpt-5.4-mini`), endpoint `.../openai/v1` (nouvelle API unifiée).
- **`ops/azure_adapter.py`** (nouveau, non fourni) : adaptateur entre
  `ops/drift_proxy.py` [FOURNI] et le vrai endpoint Azure. Nécessaire car ce
  fournisseur/endpoint rejette `?api-version=...` (toujours ajouté par le
  proxy fourni) et le modèle refuse `max_tokens` (attend
  `max_completion_tokens`). Câblé via le service docker `azure-adapter` ;
  `AZURE_AI_ENDPOINT` (vu par le proxy) pointe dessus, la vraie URL Azure est
  dans `AZURE_AI_REAL_ENDPOINT`. Décision explicite : ne jamais modifier
  `ops/drift_proxy.py` ni `app/llm_client.py` (fournis) pour ce problème.
  Détail : `CHANGELOG.md` (2026-09-21, « environnement Docker »).
- `/v1/analyse` vérifiée fonctionnelle avec cette config (curl, `client_v1.py`,
  `make test-integration`).

## Conventions de travail (utilisateur)

- Français pour les échanges, code en anglais commenté en français.
- Simple > flexible, YAGNI, modifications ciblées.
- Suivi dans ce dépôt : `CHANGELOG.md` (réalisé, ordre inverse), `TODO.md`
  (reste à faire), `MEMORY.md` (ce fichier). Écarts de conception documentés
  dans `docs/conception_revue/`, jamais dans `conception_figee/`.
- Pas de commit sans accord explicite de l'utilisateur.
- Un seul agent par défaut ; subagents exceptionnels, justifiés par un gain
  clair.
- L'utilisateur est développeur PHP confirmé, étudiant en dev IA agentique —
  pédagogie bienvenue.
