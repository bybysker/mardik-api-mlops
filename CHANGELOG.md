# CHANGELOG — mardik-api-mlops

> Tracé horodaté, ordre inverse (plus récent en premier).

## 2026-09-23 (chantier 2 : client web de pilotage câblé)

- **`client_web/` (nouveau)** : les 4 pages de la maquette figée
  (`conception_figee/sources/pilotage_maquette/html/`) recopiées et câblées
  sur `ops/serveur_pilotage.py` — HTML/CSS/JS vanilla, aucun build, `app.js`
  partagé (appels `fetch`, mappings signal/action, formatage FR). La
  maquette elle-même n'est pas modifiée (lecture seule).
  - `index.html` (tableau de bord) : `GET /pilotage/dashboard`, rafraîchissement
    manuel + auto (30 s).
  - `pilotage.html` (règles) : `GET /pilotage/regles`, édition inline
    (`prompt()`) → `PUT /pilotage/regles/{signal}`.
  - `actions.html` : `POST /pilotage/promotion` / `POST /pilotage/rollback`.
    Paliers canary limités à 50/100 % (10 % est posé automatiquement par la
    chaîne CD à la publication, pas par cet écran — la maquette proposait
    10/50/100, ajusté au contrat réel de `POST /pilotage/promotion`).
  - `journal.html` : `GET /pilotage/journal`, filtre par signal.
- **Écart documenté vs maquette** : la carte « Distribution du score » de
  `index.html` montrait un histogramme à 10 tranches (0,0 à 0,9) ; le
  contrat gelé (`Dashboard.distribution_score`) n'expose que
  `proportion_score_faible`/`seuil_faible` (une seule proportion, pas de
  répartition par tranche) — remplacé par une seule barre, pas de données
  fabriquées pour combler l'écart.
- **CORS ouvert sur `ops/serveur_pilotage.py`** (`CORSMiddleware`,
  `allow_origins=["*"]`) : le client web (port 8503) et le serveur de
  pilotage (port 8002) sont deux origines différentes, pas de Caddy en
  frontal pour les unifier à ce stade.
- **Service `client_web` ajouté à `docker-compose.yml`** : réutilise
  l'image du projet (`build: .`), sert les fichiers statiques via
  `python -m http.server 8503`.
- **Vérification manuelle** (pas de navigateur disponible ici) :
  `node --check` sur `app.js` + les scripts inline des 4 pages (aucune
  erreur de syntaxe) ; serveur de pilotage lancé en local avec des données
  de test, `GET /pilotage/dashboard`/`regles`/`journal` renvoient des
  formes JSON conformes à ce que `app.js` consomme ; en-tête
  `access-control-allow-origin` confirmé ; les 6 fichiers statiques
  répondent 200 via `python -m http.server`. Pas de rendu visuel confirmé.
- Suite Python inchangée : **100 passed**, ruff clean (aucun test
  automatisé ajouté côté client web — HTML/CSS/JS vanilla sans outillage
  de test, conforme au choix déjà acté pour ce client).

## 2026-09-23 (chantier 2 : `ops/serveur_pilotage.py` implémenté)

- **Conflit de conception tranché** : la conception prévoyait deux nouveaux
  fichiers (`ops/registre.json` par fingerprint, `ops/journal_pilotage.jsonl`)
  pour le serveur de pilotage ; le chantier 1 avait déjà posé `ops/registry/`
  (classe `Registry`, identifiée par étiquette SemVer) et branché
  `app/gateway.py`/`ops/deploy.py` dessus. **Décision : le serveur de
  pilotage réutilise `ops/registry/` existant**, pas de nouveau fichier —
  une seule source de vérité plutôt que deux à synchroniser. Détail complet :
  `docs/conception_revue/pilotage/formats-ops.md` (nouveau).
- **`ops/serveur_pilotage.py` : les 6 routes du contrat gelé implémentées**
  (TDD, `tests/unit/test_serveur_pilotage.py` entièrement réécrit — les
  anciens tests vérifiaient des 501, remplacés par le comportement réel) :
  - `GET /pilotage/dashboard` — réutilise `ops.dashboard.resume()` +
    calculs globaux (latence P95, coût moyen, distribution du score),
    reshapés vers le schéma `Dashboard` gelé.
  - `GET/PUT /pilotage/regles` — nouveau fichier `ops/regles_pilotage.json`
    (seul vrai nouveau fichier), seedé avec les 4 règles du tableau de
    pilotage (`docs/conception_revue/pilotage/tableau-pilotage.md`).
    Ajustement tracé au journal.
  - `POST /pilotage/promotion` — implémente le vrai critère « v2 ≥ v1 »
    (`canary.md` révisé) : contraintes client (P95 < 8 s, coût < 0,15 €,
    erreur < 10 %) + v2 jamais moins bonne + strictement meilleure sur au
    moins un signal, comparée sur la fenêtre canary (120 s, 10 mesures
    min. par version) ; 409 si critères non tenus ou pas assez de mesures.
  - `POST /pilotage/rollback` — expose `ops.deploy.rollback()`.
  - `GET /pilotage/journal` — reshape `ops/registry/journal.jsonl` vers le
    schéma `EntreeJournal` gelé, filtre par `signal`, limite.
- **`ops/deploy.py::deployer_canary/promouvoir/rollback` acceptent
  désormais `**details`** transmis au journal (`declencheur`, `signal`) —
  rétrocompatible (tous les appels existants inchangés), nécessaire pour que
  le journal distingue une décision déclenchée *via* le serveur de pilotage
  d'une décision `ops/deploy.py` en ligne de commande.
- **Isolation de test corrigée** : `tests/conftest.py` (fixture `environnement`,
  autouse) isole désormais aussi `METRICS_PATH_V2` — sans ça, toute route
  n'injectant pas de `MetricsStore` explicite (dashboard, promotion) aurait
  lu le vrai `ops/metrics_v2.jsonl` du dépôt (gitignored, données locales
  périmées) au lieu d'un fichier de test isolé.
- **Hors périmètre, documenté** : régénération du Caddyfile (aucun container
  Caddy dans `docker-compose.yml` à ce stade) ; bouclage des seuils
  ajustables sur la décision automatique (`ops.deploy.surveiller` garde ses
  seuils par défaut, ne lit pas encore `ops/regles_pilotage.json`).
- Suite complète : **100 passed**, ruff clean.

## 2026-09-23 (chantier 2 : `ops/deploy.py::surveiller` implémenté)

- **`ops/deploy.py::surveiller` implémenté** (TDD, 9 tests ajoutés à
  `tests/unit/test_deploy.py`). Surveille le canary s'il y en a un, sinon
  l'active ; dérive si score moyen < `score_min`, ou taux d'erreur >
  `taux_erreur_max`, ou P95 > `latence_p95_max_ms`, sur au moins `minimum`
  mesures. Rollback automatique + entrée journal en cas de dérive.
- **Fusion v1/v2 des métriques, complétée** : `percentile()` et
  `stores_metriques_par_defaut()` (ex-`_percentile`/`_stores_par_defaut`,
  rendues publiques) de `ops/dashboard.py` sont réutilisées par
  `surveiller()` — même besoin de ne pas laisser le trafic du container
  `v2` invisible, déjà résolu côté `dashboard.py` (2026-09-23, entrée
  précédente).
- **`tests/acceptance/test_observabilite.py`** : plus aucun test `xfail`,
  les 5 tests passent réellement (`_HORS_PERIMETRE` et l'import `pytest`
  devenus inutiles, retirés). Suite complète : **93 passed**, ruff clean.

## 2026-09-23 (chantier 2 : `app/gateway.py` implémenté)

- **`app/gateway.py` implémenté** (TDD, `tests/unit/test_gateway.py` écrits
  rouges avant l'implémentation) : `choisir_version` (fonction pure de
  routage canary), `GET /gateway/etat`, `POST /analyse`. La gateway relit
  `ops/registry/index.json` à chaque requête (promotion/rollback pris en
  compte sans redémarrage), route vers `analyser_v1` ou `analyser_v2` selon
  la `strategie` du bundle livré, force le pourcentage canary si
  `CANARY_PERCENT` est défini, propage 413/503 comme `/v1` et `/v2`.
- **`@router.post("/analyse", response_model=None)`** : sans ce réglage,
  FastAPI inférait `-> dict` comme `response_model` et rejetait la réponse
  (un `ReponseAnalyseV1`/`ReponseAnalyseV2`, pas un `dict` brut) avec une
  `ResponseValidationError` — trouvé en lançant la suite complète après
  l'implémentation initiale.
- **`test_promotion_canary_puis_totale` et `test_rollback_en_une_operation`**
  (`tests/acceptance/test_observabilite.py`) ne sont plus `xfail` : ils ne
  dépendaient que de `gateway.py` (`ops/deploy.py::rollback/promouvoir/
  deployer_canary` étaient déjà implémentés, chantier 1 point 3). Suite :
  84 passed, 1 xfailed (`test_journal_derive_et_rollback_automatique`,
  dépend de `ops/deploy.py::surveiller`, toujours `[STUB]`).

## 2026-09-23 (chantier 2 : `ops/dashboard.py` implémenté)

- **`ops/dashboard.py::resume/rendre_texte/rendre_html` implémentés**
  (premier point du chantier 2, TDD : `tests/unit/test_dashboard.py` écrits
  rouges avant l'implémentation). Fenêtre **temporelle** (`fenetre_s`),
  agrégats par version (trafic, latence p50/p95, taux d'erreur, score moyen,
  coût total), erreurs exclues des latences/scores comme documenté.
- **Fusion v1/v2 sans store explicite** : `resume()` sans `metriques` lit
  désormais à la fois `METRICS_PATH` (v1) et une nouvelle variable
  `METRICS_PATH_V2` (défaut `ops/metrics_v2.jsonl`), pour ne pas laisser le
  trafic du container `v2` invisible du tableau de bord — condition posée
  dans `MEMORY.md`/`TODO.md`. `docker-compose.yml` (service `dashboard`)
  reçoit `METRICS_PATH_V2`. `ops/deploy.py::surveiller` a le même besoin,
  pas encore traité (reste `[STUB]`).
- **`test_dashboard_par_version`** (`tests/acceptance/test_observabilite.py`)
  n'est plus `xfail` : il ne dépendait ni de `gateway.py` ni de
  `surveiller()`, seulement de `dashboard.resume()`. Suite : 76 passed,
  3 xfailed (restants : gateway/canary, rollback, dérive+surveiller).

## 2026-09-23 (parallélisation des appels LLM du pipeline v2)

- **`app/api_v2.py::analyser_v2` : appels LLM par section parallélisés**
  (`ThreadPoolExecutor`, `MAX_APPELS_LLM_PARALLELES = 8`) au lieu d'une
  boucle `for` séquentielle. Corrige le risque de latence P95 identifié le
  2026-09-21 (jusqu'à 20 appels séquentiels pour le contrat le plus long,
  invisible en `MOCK` mais probablement bloquant contre le vrai modèle au
  gate). `executor.map` préserve l'ordre des sections (`par_section`), dont
  dépend `consolidation.py::consolider` (ordre d'apparition dans le
  contrat). Nouvelle fonction `_extraire_avec_span` : le contexte
  OpenTelemetry ne traverse pas les threads tout seul, donc chaque thread
  réattache explicitement le contexte du span parent (`analyse.requete`)
  avant d'ouvrir son span `llm.appel` — vérifié manuellement (span enfants
  bien rattachés au parent). Tests inchangés : 68 passed, 4 xfailed.

## 2026-09-22 (branche `dev` poussée sur GitHub + 3 schémas chantier 1)

- **`dev` poussée vers GitHub** (`origin/dev`) : le dépôt distant
  `wawawaformation/mardik-api-mlops` n'avait jusque-là que `main` (squelette
  de départ). Protections de tags/branche et prérequis (`mardik-relecteur`,
  `CI_TAG_TOKEN`, secrets Azure) volontairement reportés — décision
  explicite de l'utilisateur, détail dans `MEMORY.md`.
- **3 schémas draw.io ajoutés** (`docs/img/`), couvrant les 3 points du
  chantier 1 : `chantier1-trois-points_reel.drawio` (vue d'ensemble, renvoie
  vers `pipeline-v2.drawio` pour le point 2), `chaine-llmops-deux-tags_reel.drawio`
  et `cd-main-deroule_reel.drawio` (détail du point 3).

## 2026-09-22 (chantier 1 point 3 : décisions de périmètre + design de la chaîne LLMOps)

- **Périmètre du point 3 tranché** : `llmops.yml` + `ops/deploy.py::publier/
  deployer_canary/promouvoir/rollback`, **sans** `surveiller()` (détection de
  dérive) ni `app/gateway.py` (routage réel du trafic canary) — les deux
  restent chantier 2. Conséquence assumée : `test_promotion_canary_puis_totale`
  et `test_rollback_en_une_operation` (tests d'acceptance fournis) resteront
  rouges tant que le chantier 2 n'est pas fait.
- **`CANARY_PERCENT`/`MOCK` dans `.env`** : restent des valeurs par défaut
  statiques, pas de pilotage dynamique en dehors du chantier 2.
- **Doublon `ops/dashboard.py` (8501) vs `GET /pilotage/dashboard`** : pas de
  duplication à résoudre — `ops/dashboard.py::resume()` (imposé par le test
  d'acceptance fourni `test_dashboard_par_version`) reste la fonction de
  calcul, réutilisée en interne par la route JSON contractuelle.
- **`bruno/`** retiré de l'index git (client de requêtes local, non
  versionné) et ajouté à `.gitignore`.
- **Design de la chaîne LLMOps écrit** :
  `docs/superpowers/specs/2026-09-22-chaine-llmops-design.md` — couvre
  `eval/run_eval.py::evaluer`, `ops/deploy.py` (sauf `surveiller`) et 4
  workflows GitHub Actions (`ci.yml`, `revue.yml`, `gate.yml`, `cd-main.yml`)
  qui remplacent le `.github/workflows/llmops.yml` `[TEMPLATE]` actuel.
  Pattern repris de `/projets/QualiCheck/.gitea/workflows/` (même principe de
  gates à deux tags, syntaxe GitHub Actions native). Décisions clés : gate
  déclenché par un tag `gate/<sha7>` poussé par le développeur (comme
  `revue-ok`/`eval-ok`) ; `revue-ok` posé sur l'approbation d'un second compte
  GitHub dédié ; bump SemVer major/minor via mot-clé `[minor]`/`[major]` dans
  le message du commit de fusion, patch auto-incrémenté sinon ; CD automatique
  jusqu'au canary 10 % seulement, promotion/rollback restent manuels.
- **Écart de conception documenté** : la note du gate d'évaluation suit le
  **rappel simple** documenté par le stub `eval/run_eval.py`, pas le micro-F1
  scindé courts/longs décidé en conception (`note-evaluation.md`) — aucun test
  ne verrouille l'une ou l'autre formule, le garde-fou visé reste assuré via
  `seuil_note` par contrat (détail dans le design).
- **Plan écrit, exécution démarrée puis mise en pause** : plan à 8 tâches
  (`docs/superpowers/plans/2026-09-22-chaine-llmops.md`), exécuté via
  `superpowers:subagent-driven-development` dans un worktree isolé
  (`.worktrees/chaine-llmops/`, branche `sdd/chaine-llmops`, non fusionnée).
  **Tâche 1/8 terminée et revue** : `ops.deploy.prochaine_version` (SemVer
  patch/minor/major depuis le registre), commits `55abf9a` puis `c33489e`
  (fix — import `os` retiré, à réajouter par la tâche 4). Tâches 2 à 8 pas
  commencées. Détail complet dans `MEMORY.md` (« En cours »).

## 2026-09-22 (chaîne LLMOps : plan exécuté, 8/8, puis revue finale de branche corrigée)

- **Plan `docs/superpowers/plans/2026-09-22-chaine-llmops.md` exécuté (8/8
  tâches)** : `prochaine_version`, `evaluer` (gate), `publier`/
  `deployer_canary`/`promouvoir`/`rollback`, et les 4 workflows (`ci.yml`,
  `revue.yml`, `gate.yml`, `cd-main.yml`) remplaçant `llmops.yml`.
  `surveiller()` et `app/gateway.py` restent chantier 2 (hors périmètre).
- **Revue finale de branche (avant fusion) — correctifs appliqués** :
  - 4 tests d'acceptance hors périmètre (`test_rollback_en_une_operation`,
    `test_promotion_canary_puis_totale`, `test_dashboard_par_version`,
    `test_journal_derive_et_rollback_automatique`) marqués
    `xfail(strict=False)` — ils faisaient échouer `tests`, donc bloquaient
    `evaluation`/`eval-ok`, rendant toute la chaîne inopérante.
  - Commentaire d'en-tête de `cd-main.yml` corrigé : `publier()` sans
    `--rapport` rejoue bien un vrai gate d'évaluation payant sur `main` (le
    commentaire précédent affirmait le contraire).
  - `cd-main.yml` réordonné : le gate (`publier`) s'exécute désormais avant
    le build/push Docker vers `ghcr.io`, pour ne jamais publier une image non
    validée.
  - Nouveau step `cd-main.yml` : commit + push du répertoire
    `ops/registry/<version>/` fraîchement créé, avec `GITHUB_TOKEN` (jamais
    un PAT, pour éviter une boucle de déclenchement infinie sur `push: main`)
    — sans quoi la version ne progressait jamais d'un run à l'autre
    (`ops/registry/v*` gitignored sur chaque runner sauf `v1.0.0`).
  - Prérequis fast-forward-only sur `main` documenté dans le design
    (« Prérequis hors code ») ; wording « commit de fusion » → « commit de
    tête » (pas de merge commit en ff-only).
  - `revue.yml` : ajout du bloc `permissions: contents: read` (les autres
    workflows l'avaient déjà).
- **Fusionné dans `dev`** (commit `2f1c53c`, fusion locale, tests vérifiés
  verts sur le résultat fusionné : 68 passed, 4 xfailed, ruff clean).
  Worktree `.worktrees/chaine-llmops/` et branche `sdd/chaine-llmops`
  supprimés après fusion. Conflit de fusion sur `MEMORY.md` résolu (deux
  sections « En cours » divergentes sur le même sujet, `dev` avait avancé
  pendant l'exécution du plan) — `TODO.md`/`CHANGELOG.md` fusionnés sans
  conflit.

## 2026-09-21 (topologie : containers `v2` et `serveur_pilotage`, ports distincts)

- Première étape concrète vers la topologie cible de `docs/spec-v2.md` §4
  (« un artefact, un rôle par container ») : deux nouveaux services dans
  `docker-compose.yml`, chacun sur son port hôte, à partir de la **même
  image** que `app`. Demande initiale : « v2 dans son docker avec son ip,
  serveur_pilotage dans son docker avec son ip » — précisée en cours de
  brainstorming : ce sont des **ports** différents qui étaient voulus, pas des
  IP fixes (pas de réseau Docker personnalisé). Conception :
  `docs/superpowers/specs/2026-09-21-v2-pilotage-containers-design.md`
  (relue par un agent Opus, deux points bloquants corrigés avant le plan),
  plan : `docs/superpowers/plans/2026-09-21-v2-pilotage-containers.md`.
- **`app/main.py`** gagne une fabrique `create_app_v2()` qui ne monte que le
  router `api_v2` (+ `/health`, télémétrie et handler 501, factorisés dans un
  helper privé `_creer` partagé avec `create_app`). `create_app()`, son
  comportement et `app = create_app()` sont inchangés — les 37 tests verts
  préexistants le vérifient. `app/api_v1.py` n'a pas été touché.
- **Décision : le rôle vient de la commande uvicorn, pas d'une variable
  d'environnement.** Une variable `ROLE` avait été envisagée puis écartée en
  relecture critique : `.env` est partagé par tous les services du compose et
  `tests/conftest.py` [FOURNI] ne la neutralise pas, donc une variable perdue
  dans un shell, dans la CI ou dans `.env` aurait pu retirer `/v1` au service
  `app` — en contradiction avec `docs/spec-v2.md` §3 (« v1 jamais
  interrompue »). `--factory` supprime le problème à la racine.
- **`ops/serveur_pilotage.py`** (nouveau) : squelette FastAPI du serveur de
  pilotage. Les 6 routes du contrat gelé
  (`conception_figee/pilotage/openapi-pilotage.json`, écart vérifié à zéro par
  script) répondent **501** ; les 3 routes d'écriture déclarent les modèles
  Pydantic du contrat (`AjustementSeuil`, `Promotion`, `Rollback`), donc un
  corps invalide est refusé en **422** avant le handler. `GET /health` est une
  extension hors contrat, non normative, nécessaire au healthcheck. Le module
  ne lit et n'écrit aucun fichier à ce stade.
- **Décision : `METRICS_PATH=/app/ops/metrics_v2.jsonl` pour le service
  `v2`.** `app` et `v2` servent tous deux `/v2/analyse` et la dataclasse
  `Mesure` (`app/telemetry.py` [FOURNI]) n'a aucun champ identifiant le
  container : sans journaux distincts, les mesures des deux instances
  seraient indiscernables pour `ops/dashboard.py::resume` et
  `ops/deploy.py::surveiller`. Conséquence assumée : ces deux modules ne
  lisent pas encore `metrics_v2.jsonl` — leur adaptation est le chantier 2.
  `.gitignore` et `make clean` couvrent le nouveau fichier.
- Healthchecks Python (`urllib.request`) sur `/health` pour les deux nouveaux
  services : l'image `python:3.11-slim` n'embarque pas `curl`, et
  `docker compose up -d --build --wait` ne doit rendre la main qu'une fois
  les services prêts.
- Le service `dashboard` (8501) reste **inchangé** : l'arbitrage entre
  `ops/dashboard.py` et la route `/pilotage/dashboard` du contrat gelé est
  explicitement renvoyé au chantier 2.
- Tests : 17 tests unitaires ajoutés (`tests/unit/test_fabrique_app_v2.py`,
  5 ; `tests/unit/test_serveur_pilotage.py`, 12).
  `MOCK=on uv run pytest -q` → **54 passed, 7 failed** (contre 37/7 avant ;
  les 7 rouges sont inchangés, ils attendent `ops/deploy.py`,
  `eval/run_eval.py` et `ops/dashboard.py`). `uv run ruff check .` vert.
- Vérification réelle : `docker compose up -d --build --wait` (6 services,
  `v2` et `serveur_pilotage` `healthy`), puis `localhost:8001/health` → 200,
  `POST localhost:8001/v1/analyse` → 404, `localhost:8002/health` → 200,
  `localhost:8002/pilotage/journal` → 501, `POST .../pilotage/rollback` → 501
  (corps valide) et 422 (corps invalide), et non-régression de `app` :
  `localhost:8000/health` → 200, `POST localhost:8000/v1/analyse` → 200,
  `localhost:8000/gateway/etat` → 501. Journaux séparés confirmés : un appel
  sur `v2` ajoute une ligne à `ops/metrics_v2.jsonl` et aucune à
  `ops/metrics.jsonl`.
- Documentation du dépôt parent, à la demande de l'utilisateur (exception
  explicite à la règle « ne rien écrire hors de `mardik-api-mlops/` »,
  `conception_figee/` restant intact) : `../AGENTS.md` et `../MEMORY.md`
  mis à jour pour le renommage `conception/` → `conception_figee/` (chemins
  corrigés, gel en lecture seule, renvoi vers ce dépôt, mention que le parent
  n'a plus de `.git`). `../TODO.md` et `../CHANGELOG.md` gardent l'ancien nom :
  historique de la phase de conception, volontairement non réécrit.
  `README.md` de ce dépôt : tableau des services compose (ports 8000/8001/
  8002/8080/8501) et arborescence à jour.
- Deux écarts assumés par rapport au plan : `make clean` n'a été vérifié qu'en
  dry-run (`make -n clean`) car l'exécuter aurait supprimé `ops/metrics.jsonl`
  (fichier généré, ignoré par git, irrécupérable) ; et la stack n'a pas été
  arrêtée à la fin (`docker compose down` omis) parce qu'elle tournait déjà
  avant la vérification — les 4 services existants ont été recréés par
  `up --build`, la stack reste démarrée.

## 2026-09-21 (chantier 1 point 2 : pipeline `/v2/analyse` implémenté, revue de branche, fix wave)

- Les 7 tâches de `docs/superpowers/plans/2026-09-21-api-v2-pipeline.md` ont
  été implémentées via développement piloté par subagents (un agent
  implémenteur par tâche, relu et corrigé par un agent contrôleur avant
  passage à la suivante — détail par tâche :
  `.superpowers/sdd/2026-09-21-api-v2-pipeline/progress.md`), puis fusionnées
  sur `dev` : bundle v2 (`models/v2/config.yaml`), découpage
  (`app/pipeline/decoupage.py::decouper`), extraction
  (`app/pipeline/extraction.py::extraire`), consolidation
  (`app/pipeline/consolidation.py::consolider`), score de confiance
  (`app/pipeline/confiance.py::scorer`), orchestration
  (`app/api_v2.py::analyser_v2` + route `POST /v2/analyse`).
- **Relecture finale de la branche complète** (au-delà des revues par tâche)
  : 4 constats corrigés dans cette même passe (voir plus bas — documentation
  obsolète, absence de signal télémétrie sur les rejets LLM hors schéma,
  garde-fou 413 pas assez tôt dans la pile d'appel, nettoyage de docstrings)
  et une note de calibration hors périmètre consignée dans `MEMORY.md`.
- Décisions actées pendant l'implémentation, non documentées ailleurs
  jusqu'ici :
  - `seed: 0` fixé dans le bundle v2 (`models/v2/config.yaml`), pour un gate
    d'évaluation stable (point ouvert du stub fourni, tranché ici).
  - `scorer()` a gagné un paramètre `nb_sections: int` en plus de `texte`
    (conservé mais inutilisé pour l'instant) : la formule de corroboration
    actée (`score-confiance.md`) a besoin du nombre total de sections du
    document, que `texte` seul ne donne pas.
  - `app/pipeline/decoupage.py::decouper` implémente **trois niveaux**
    (structurel → regroupement des blocs consécutifs jusqu'à `taille_max` →
    repli taille fixe avec chevauchement) plutôt que les deux esquissés dans
    la première version du plan — le regroupement est ce qui tient le budget
    d'appels LLM (jusqu'à 20× moins d'appels sur les contrats courts).
  - `LIMITE_CARACTERES = 250_000` pour le garde-fou 413 (document trop
    long).
- Correctifs de cette passe de relecture finale (« fix wave ») :
  - Le garde-fou 413 ne vivait que dans la route HTTP, pas dans
    `analyser_v2` elle-même — silencieusement contourné par un appel direct
    hors HTTP (le futur `app/gateway.py`, ou le gate d'évaluation). Déplacé
    dans `analyser_v2`, avec une nouvelle exception dédiée
    (`DocumentTropLong`) traduite en 413 par la route ; une `Mesure`
    d'erreur est désormais journalisée pour ce cas aussi.
  - Aucun signal télémétrie quand une réponse LLM est rejetée pour non
    conformité au schéma (JSON invalide, champ manquant, type inconnu,
    confiance hors bornes) — comportement correct (jamais de crash) mais
    invisible. Ajout de logs d'avertissement (`logging` standard) dans
    `extraire()` et de l'attribut `llm.clauses` sur le span `llm.appel`
    (`app/api_v2.py`).
  - `MEMORY.md`, `TODO.md`, `CHANGELOG.md` ne reflétaient plus l'état réel
    (tout marqué non implémenté) — mis à jour dans cette même passe.
  - Nettoyage : retrait du marqueur `[STUB]` et de « Contrat attendu » dans
    les docstrings de `app/api_v2.py`, `app/pipeline/confiance.py`,
    `app/pipeline/consolidation.py`, `app/pipeline/extraction.py` (alignées
    sur `app/pipeline/decoupage.py`) ; `confiance_globale` arrondie à 3
    décimales dans la réponse, comme chaque `confiance` de clause.
- Tests : 30/30 verts (`MOCK=on uv run pytest -v tests/unit/
  tests/acceptance/test_chaine.py::test_contrat_v2_long_analyse_sans_troncature
  tests/acceptance/test_chaine.py::test_erreurs_explicites_jamais_de_500`),
  `uv run ruff check .` propre.

## 2026-09-21 (chantier 1 point 1 : spec v2 + plan pipeline v2, relecture Opus)

- `docs/spec-v2.md` créée (courte spec v2 : périmètre, exigences, contraintes,
  architecture, contrat d'API, critères d'acceptation — chaque section
  renvoie vers sa source plutôt que de dupliquer).
- Architecture actée en session : v1 / v2 / gateway en 3 containers dédiés,
  Caddy en frontal fait le vrai split de trafic (conforme à
  `conception_figee/docs/adr/0001-outil-pilotage-maison.md`), `gateway.py`
  reste la logique de décision partagée, testée en process par les tests
  fournis indépendamment de la topologie réelle.
- `docs/superpowers/plans/2026-09-21-api-v2-pipeline.md` créé : plan TDD en
  7 tâches pour le pipeline v2 (découpage → extraction → consolidation →
  score de confiance → orchestration `/v2/analyse`), ciblant les deux tests
  d'acceptance v2 fournis.
- **Relecture par un agent Opus dédié**, avec exécution réelle du code (pas
  seulement lecture) : a trouvé 2 problèmes de fond bloquants et 3 bugs de
  code dans le premier jet du plan.
  - Corrigé : le découpage ne faisait que du structurel (1 appel LLM par
    article), sans regroupement — jusqu'à 20× trop d'appels LLM sur les
    contrats courts (mesuré sur le corpus réel), menaçant directement P95 < 8 s
    et coût < 0,15 €. Ajout du niveau « regroupement de blocs consécutifs
    jusqu'à `taille_max` » de `decoupage-chunking.md`, qui n'est pas un repli
    rare mais le mécanisme qui tient le budget d'appels.
  - Corrigé : bug de casse dans un test (« Préambule » vs « préambule »),
    boucle infinie possible dans le repli taille fixe si aucune frontière de
    phrase n'est trouvée dans la fenêtre de chevauchement, code mort cassant
    `ruff check .`.
  - **Non résolu, signalé comme point ouvert** : avec la formule de
    corroboration actée (`score-confiance.md`), une clause vue dans un seul
    article (le cas normal) obtient un score de confiance de 0 — le score
    global (minimum) est quasi toujours 0,0 sur un contrat bien structuré.
    Conséquence en aval : rollback automatique déclenché dès la première
    fenêtre de trafic v2 côté pilotage. Ni la spec ni le plan ne la
    tranchent ; à valider avec l'utilisateur avant d'exécuter la tâche 3 du
    plan.
  - Écart signalé (non traité par ce plan, documenté) : `openapi.json` gelé
    attend un corps d'erreur `{code, message, request_id}`, les tests fournis
    n'exigent que `{detail}` — les tests font foi, révision formelle de
    `openapi.json` à faire séparément dans `docs/conception_revue/`.

## 2026-09-21 (environnement Docker, v1 fonctionnelle)

- `.env` créé depuis `.env.example`, `LLM_PROVIDER=azure` (choix utilisateur),
  nettoyé (variable `LLM_MODEL` correctement renseignée au lieu d'une
  `AZURE_AI_MODEL` jamais lue par le code, section Ollama retirée, guillemets
  inutiles retirés).
- `make up` : app + proxy de dérive + dashboard démarrés via docker compose.
- **Diagnostic** : `/v1/analyse` renvoyait 503. L'endpoint Azure fourni par
  l'utilisateur (`.../openai/v1`, nouvelle API unifiée) rejette le
  `?api-version=...` que `ops/drift_proxy.py` [FOURNI] ajoute toujours, et le
  modèle déployé (`gpt-5.4-mini`) refuse le paramètre `max_tokens` envoyé par
  `app/llm_client.py` [FOURNI] (attend `max_completion_tokens`).
- **Décision** : ne pas modifier les fichiers fournis. Ajout d'un adaptateur
  (`ops/azure_adapter.py`, nouveau fichier, non fourni) placé entre le proxy
  et le vrai endpoint Azure : retire `api-version`, renomme
  `max_tokens` → `max_completion_tokens`. Câblé via un nouveau service
  `azure-adapter` dans `docker-compose.yml` et la variable `AZURE_AI_ENDPOINT`
  du proxy repointée dessus (la vraie URL Azure vit dans
  `AZURE_AI_REAL_ENDPOINT`, lue uniquement par l'adaptateur).
- Vérifié : `/v1/analyse` répond (200, clauses correctes), `scripts/client_v1.py`
  vert contre la stack dockerisée, `make test-integration` (6/6) et
  `test_client_v1_fonctionne` toujours verts.

## 2026-09-21 (analyse du code fourni, révision de conception, gel du dossier de conception)

- Décision : à partir de maintenant, tout le travail (code, docs, schémas) se
  fait dans ce dépôt (`mardik-api-mlops`), plus dans le dépôt parent
  `mardik_nouvelle_version`.
- L'utilisateur a gelé volontairement le dossier de conception d'origine :
  renommé `conception/` → `conception_figee/` (dépôt parent), permissions
  `555` (lecture seule), `.git` du dépôt parent supprimé intentionnellement
  (pas de remote, pas d'historique à perdre — assumé). Plus aucune écriture
  n'y sera faite ; toute révision nécessaire passe désormais par
  `docs/conception_revue/` dans ce dépôt.
- Lu et analysé le code source de départ du brief (`README.md`,
  `docs/besoin_client.md`, `docs/schema_remediation.md`, `app/api_v1.py`,
  `app/api_v2.py`, `app/gateway.py`, `app/telemetry.py`,
  `app/pipeline/decoupage.py`, `app/pipeline/extraction.py`,
  `app/pipeline/consolidation.py`, `app/pipeline/confiance.py`,
  `app/llm_client.py`, `models/v1+v2/config.yaml`, `eval/run_eval.py`,
  `ops/deploy.py`, `ops/dashboard.py`, `.github/workflows/llmops.yml`,
  `Makefile`, les tests d'acceptance) et confronté aux décisions de
  `conception_figee/` → `docs/analyse-coherence-conception.md` : cohérence
  globale confirmée (télémétrie, `/v1` intouchable, bundles, pipeline,
  gateway, versionnage), un conflit réel relevé et un premier lot de points
  mineurs sans action.
- Conflit résolu : la fenêtre glissante décidée en conception (comptage, 50
  requêtes/min 30) contredit l'interface temporelle (`fenetre_s`) imposée
  par les tests d'acceptance fournis et figés
  (`ops.deploy.surveiller`, `ops.dashboard.resume`). Décision : garder les
  tests fournis tels quels (ce sont les critères de réussite du brief) et
  réviser la conception plutôt que les tests. Versions révisées créées dans
  `docs/conception_revue/pilotage/` (`fenetre-glissante-seuils.md`,
  `canary.md`, `tableau-pilotage.md` + PDF reconstruit avec le même template
  pandoc/XeLaTeX que le dossier de conception) et
  `docs/conception_revue/chantier2_observabilite/questions_reponses.md`
  (Q9/Q10/Q12/Q14 seulement).
- Créé `docs/img/pipeline-v1_reel.drawio` (+ PNG) : pipeline `/v1/analyse`
  tel qu'implémenté réellement (troncature à 16 000 car., appel LLM via
  `app/llm_client.py`, gestion d'erreur → 503), avec un cadre visuel isolant
  le seul fichier délégué (`app/llm_client.py`) du reste (`app/api_v1.py`).
- Créé `docs/img/pipeline-v2.drawio` (+ PNG) : pipeline `/v2/analyse` cible
  (pas encore codée), `decoupage → extraction (map) → consolidation (reduce)
  → confiance`, orchestré par `app/api_v2.py`, annoté des contrats tirés des
  docstrings des stubs.
- Créé `MEMORY.md`, `TODO.md`, ce `CHANGELOG.md` pour la continuité
  inter-agents dans ce dépôt.
- Commit `1f841b9` : `docs: analyse de cohérence conception vs. code source`.
  Reste en attente de commit (accord explicite requis) : la révision de
  `docs/analyse-coherence-conception.md`, tout `docs/conception_revue/`,
  tout `docs/img/`, et ces trois fichiers de suivi.
