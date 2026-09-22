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

**Chantier 1 point 2 (pipeline `/v2/analyse`) implémenté et testé**, via le
plan `docs/superpowers/plans/2026-09-21-api-v2-pipeline.md` exécuté en
subagent-driven development (7 tâches, revue par tâche + revue finale de
branche complète). `app/pipeline/decoupage.py::decouper`,
`app/pipeline/extraction.py::extraire`, `app/pipeline/consolidation.py::consolider`,
`app/pipeline/confiance.py::scorer` et `app/api_v2.py::analyser_v2` (+ route
`POST /v2/analyse`) sont tous fonctionnels, plus `models/v2/config.yaml`
(bundle, stratégie `map_reduce_clauses`). Couverture : 27 tests unitaires
(bundle + pipeline + orchestration) et les 2 tests d'acceptance ciblés
(`test_contrat_v2_long_analyse_sans_troncature`,
`test_erreurs_explicites_jamais_de_500`), tous verts.

Décisions actées pendant l'implémentation, non documentées ailleurs — détail
dans `CHANGELOG.md` (entrée du jour) :
- `seed: 0` fixé dans le bundle v2 (`models/v2/config.yaml`), pour un gate
  d'évaluation stable.
- `scorer()` a gagné un paramètre `nb_sections: int` (la formule de
  corroboration a besoin du nombre total de sections, que `texte` seul ne
  donne pas) ; `texte` est conservé dans la signature pour compatibilité mais
  inutilisé pour l'instant.
- `decoupage.py::decouper` implémente **trois niveaux** (structurel →
  regroupement des blocs consécutifs jusqu'à `taille_max` → repli taille
  fixe avec chevauchement) plutôt que les deux esquissés initialement dans le
  plan — le regroupement est ce qui tient le budget d'appels LLM.
- `LIMITE_CARACTERES = 250_000` pour le garde-fou 413, vérifié désormais
  **dans `analyser_v2` elle-même** (pas seulement dans la route HTTP), pour
  protéger aussi les appelants directs hors HTTP (futur `app/gateway.py`).

**Toujours non implémenté, hors périmètre de ce plan** : `app/gateway.py`,
`eval/run_eval.py::evaluer`, `ops/deploy.py::*`, `ops/dashboard.py::*` —
restent `[STUB]`, `NotImplementedError`. Seuls `app/api_v1.py`,
`app/llm_client.py`, `app/telemetry.py`, `ops/drift_proxy.py`,
`ops/registry/` étaient `[FOURNI]` et fonctionnels dès le départ ; s'y
ajoutent maintenant `app/api_v2.py` et tout `app/pipeline/*`.

Deux schémas documentent l'architecture (le second est maintenant à jour
avec le code réel, pas seulement la cible) :

- le pipeline `/v1/analyse` **réel** (`docs/img/pipeline-v1_reel.drawio`) :
  tout est dans `app/api_v1.py`, seul l'appel LLM est délégué à
  `app/llm_client.py`.
- le pipeline `/v2/analyse` (`docs/img/pipeline-v2.drawio`) :
  `decoupage → extraction (map, 1 appel LLM/section) → consolidation
  (reduce) → confiance`, orchestré par `app/api_v2.py` — désormais
  implémenté tel que schématisé.

### Points connus, non corrigés ici, hors périmètre de ce plan

- **Risque de latence P95 pour le gate d'éval (chantier 1 point 3)** : les
  appels LLM par section dans `app/api_v2.py::analyser_v2` sont strictement
  séquentiels (une boucle `for`, pas de parallélisation). Mesuré sur le
  corpus réel : jusqu'à 20 appels séquentiels pour le contrat le plus long
  (c12). Invisible en mode `MOCK` (~0,2 ms/appel), donc aucun test ne le
  détecte — mais le gate d'évaluation tournera contre un vrai modèle et
  vérifie `latence_p95_ms < 8000`, contrainte que ce comportement va très
  probablement violer. La marge de coût mesurée est confortable (0,054 €
  contre 0,15 € de budget pour c12), donc paralléliser (par ex. un
  `ThreadPoolExecutor` sur les sections, en préservant l'ordre de
  `par_section` et le rattachement du span `llm.appel` par section) est le
  correctif naturel pour qui reprendra le chantier 1 point 3 — non fait ici,
  hors périmètre de ce plan.
- **Note de calibration découpage/corroboration pour le chantier 2** : le
  chevauchement (~250 car.) du repli taille fixe peut faire compter une
  clause à cheval sur deux chunks adjacents comme corroborée par la
  géométrie du découpage, pas par une détection multiple réellement
  indépendante ; à l'inverse, le regroupement de `_regrouper` peut fusionner
  des occurrences d'articles distincts dans une seule section, plafonnant
  leur corroboration à n=1. Aucun des 12 contrats du corpus ne déclenche
  aujourd'hui le repli taille fixe, donc ce biais est latent, pas actif —
  mais à garder en tête pour la calibration du score au chantier 2, puisque
  le signal de corroboration dépend en partie de la géométrie du découpage,
  pas seulement d'une détection répétée réelle par le modèle. Fait mesuré à
  l'appui de cette calibration (pas une nouvelle anomalie — la formule est
  implémentée telle qu'actée) : **100 % des scores de clause individuels,
  sur les 12 contrats du corpus, valent actuellement exactement 0,0** (pas
  seulement le minimum global — chaque clause individuellement).

## Topologie — où en est-on de « un artefact, un rôle par container » (2026-09-21)

`docs/spec-v2.md` §4 vise un artefact Docker unique et un rôle par container
(v1, v2, gateway) derrière Caddy. **Partiellement en place** :

| Service compose | Port hôte → container | Rôle |
|---|---|---|
| `app` | 8000 → 8000 | complet (v1 + v2 + gateway), confort de dev — inchangé |
| `v2` | 8001 → 8000 | `/v2/analyse` + `/health` (`create_app_v2`) |
| `serveur_pilotage` | 8002 → 8000 | squelette `/pilotage/*` (501) + `/health` |
| `proxy` | 8080 → 8080 | proxy de dérive |
| `dashboard` | 8501 → 8501 | tableau de bord (stub) — inchangé |
| `azure-adapter` | interne 9000 | adaptateur Azure |

Reste à faire : container v1 isolé, container gateway, Caddy en frontal.
Conception : `docs/superpowers/specs/2026-09-21-v2-pilotage-containers-design.md`.

- **Ce sont des ports différents qui étaient voulus, pas des IP fixes** (demande
  initiale ambiguë, précisée par l'utilisateur) : pas de réseau Docker
  personnalisé.
- **Le rôle vient de la commande uvicorn, jamais d'une variable
  d'environnement** (`--factory` sur `app.main:create_app_v2`). Raison : le
  `.env` est partagé par tous les services et `tests/conftest.py` [FOURNI] ne
  neutralise aucune variable de rôle ; une variable perdue aurait pu retirer
  `/v1` au service `app`. À ne pas ré-introduire.
- **`app` et `v2` ont des journaux de métriques distincts** :
  `ops/metrics.jsonl` et `ops/metrics_v2.jsonl`. `Mesure` [FOURNI] n'a pas de
  champ identifiant le container, deux journaux étaient le seul moyen de ne
  pas mélanger les mesures. `ops/dashboard.py` et `ops/deploy.py::surveiller`
  ne lisent encore que `ops/metrics.jsonl` (chantier 2).
- **Les 3 routes d'écriture du serveur de pilotage valident leur corps** avec
  les modèles du contrat gelé : corps valide → 501, corps invalide → 422.
- **`GET /health` du serveur de pilotage est hors contrat gelé**, non
  normatif : il n'existe que pour le healthcheck du container.
- Healthchecks en Python (`urllib.request`) et non `curl` : l'image
  `python:3.11-slim` n'embarque pas `curl`.
- Le service `dashboard` (8501) et la route `GET /pilotage/dashboard` font
  double emploi : arbitrage renvoyé au chantier 2.
- Tests : `MOCK=on uv run pytest -q` → **54 passed, 7 failed** (les 7 rouges
  attendent `ops/deploy.py`, `eval/run_eval.py`, `ops/dashboard.py`).

## Décision — périmètre du chantier 1 point 3 (2026-09-22)

**Chantier 1, point 3 (chaîne `llmops.yml` : gates → build → artefact
étiqueté → déploiement canary)** : périmètre tranché par l'utilisateur.
Point 3 = `llmops.yml` + `ops/deploy.py::publier/deployer_canary/promouvoir/rollback`,
**sans** `surveiller()` (détection de dérive + rollback automatique, qui
reste chantier 2) et **sans** `app/gateway.py` (routage réel du trafic
canary, qui reste chantier 2 aussi). Conséquence assumée :
`test_promotion_canary_puis_totale` et `test_rollback_en_une_operation`
(tests d'acceptance fournis, dépendent de `gateway.py`) resteront rouges
tant que le chantier 2 n'est pas fait — attendu, pas un défaut du point 3.
Repères déjà en main pour la suite : `conception_figee/chantier1_llmops/gel-eval-avant-fusion.md`
(mécanisme à deux tags `revue-ok`/`eval-ok`, détaillé et acté) et
`ops/deploy.py` (stub fourni, signatures des 4 fonctions restantes déjà
figées par les tests d'acceptance fournis).

Deux autres points tranchés le même jour :

- **`CANARY_PERCENT`/`MOCK` dans `.env`** : restent des valeurs par défaut
  statiques. Le pilotage dynamique du pourcentage canary relève du
  chantier 2 (registre/serveur de pilotage), pas de l'environnement de base.
- **Doublon `ops/dashboard.py` (8501) vs `GET /pilotage/dashboard`** : pas de
  duplication à résoudre. `ops/dashboard.py::resume()` reste la fonction de
  calcul (imposée par le test d'acceptance fourni `test_dashboard_par_version`
  dans `tests/acceptance/test_observabilite.py`) ; `GET /pilotage/dashboard`
  (serveur de pilotage) réutilise cette même fonction en interne plutôt que
  de recalculer l'agrégation. Le service `dashboard` (8501, `--serve`) reste
  une vue texte/HTML autonome héritée de la remédiation, en plus de la route
  JSON contractuelle. La conception (ADR 0001, Q6 de
  `conception_figee/chantier2_observabilite/questions_reponses.md`) avait été
  écrite avant d'avoir accès au stub réel et ne tranchait pas ce doublon
  explicitement ; c'est le test d'acceptance gelé qui fixe la réponse.

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
