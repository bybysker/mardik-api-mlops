# TODO — mardik-api-mlops

## Analyse préalable (fait)

- [x] Lire le code source fourni et le confronter à `conception_figee/`
      (`docs/analyse-coherence-conception.md`)
- [x] Schéma du pipeline `/v1/analyse` réel (`docs/img/pipeline-v1_reel.drawio`)
- [x] Schéma du pipeline `/v2/analyse` cible (`docs/img/pipeline-v2.drawio`)
- [x] Trancher le conflit fenêtre glissante (comptage vs. temporelle) →
      temporelle retenue, révision dans `docs/conception_revue/pilotage/`
      (`fenetre-glissante-seuils.md`, `canary.md`, `tableau-pilotage.md` + PDF,
      `questions_reponses.md` Q9/Q10/Q12/Q14)

## Chantier 1 — Le bundle v2

- [x] `models/v2/config.yaml` : stratégie `map_reduce_clauses`, prompt par
      section (titre + texte, sortie JSON contrainte), `schema_sortie`,
      température/seed pour un gate stable

## Chantier 1 — Le pipeline v2

- [x] `app/pipeline/decoupage.py::decouper` — découpage par articles, taille
      cible 6 000 car., aucune perte de texte
- [x] `app/pipeline/extraction.py::extraire` — un appel LLM par section
      (json_mode), gestion des réponses hors schéma sans planter
- [x] `app/pipeline/consolidation.py::consolider` — fusion + dédoublonnage par
      type de clause
- [x] `app/pipeline/confiance.py::scorer` — score composite (≥ 2 signaux
      indépendants ; conception : confiance LLM × stabilité inter-chunks)
- [x] `app/api_v2.py::analyser_v2` + route `POST /v2/analyse` — orchestre les
      quatre étapes ci-dessus (voir `docs/img/pipeline-v2.drawio`)

## Chantier 1 — Le gate d'évaluation

- [x] `eval/run_eval.py::evaluer` — note par version (formule libre tant que
      les seuils/comparaisons testés passent ; conception : micro-F1 scindé
      courts/longs via `seuil_note` par contrat), latence P95, coût moyen

## Chantier 1 — La chaîne LLMOps

- [x] **Plan à 8 tâches exécuté et fusionné dans `dev`** (2026-09-22,
      commit `2f1c53c`) : `docs/superpowers/plans/2026-09-22-chaine-llmops.md`.
      Détail complet dans `MEMORY.md`.
- [x] Branche `dev` poussée vers GitHub (`origin/dev`) — le dépôt distant
      n'avait que `main` (squelette de départ) jusque-là.
- [ ] **Prérequis GitHub restants, hors code, avant un premier run réel** :
      compte `mardik-relecteur` (inscription manuelle, pas automatisable via
      `gh`), secret `CI_TAG_TOKEN` (PAT à générer depuis ce compte), secrets
      Azure (`AZURE_LLM_MODEL`, `AZURE_AI_ENDPOINT`, `AZURE_AI_API_KEY`,
      `AZURE_AI_API_VERSION`), protection des tags `revue-ok/*`/`eval-ok/*`/`v*`
      (faisable via `gh api`, pas encore fait — décision explicite de
      reporter), protection de branche `main` (`main` n'a aucune protection
      active actuellement, `protected: false`). Voir `MEMORY.md`.
- [x] **Tranché (2026-09-22)** : `CANARY_PERCENT` et `MOCK` restent des
      valeurs par défaut statiques dans `.env`. Le pilotage dynamique du
      pourcentage canary relève du chantier 2 (registre/serveur de
      pilotage), pas de l'environnement de base.
- [x] `ops/deploy.py::publier/deployer_canary/promouvoir/rollback` (point 3 ;
      `surveiller` reste chantier 2 (hors périmètre, avec `app/gateway.py`),
      voir décision périmètre ci-dessus)
- [x] `ops/dashboard.py::resume/rendre_texte/rendre_html` — fenêtre
      **temporelle** (`fenetre_s`) — voir détail sous « Chantier 2 — Pilotage »
- [x] `.github/workflows/llmops.yml` — remplacé par 4 workflows séparés par
      rôle (`ci.yml`, `revue.yml`, `gate.yml`, `cd-main.yml`), mécanisme à
      deux tags (`revue-ok/<sha>`, `eval-ok/<sha>`) décrit dans
      `conception_figee/chantier1_llmops/gel-eval-avant-fusion.md`. **Exemple
      suivi (tranché 2026-09-22)** : même principe de gates que
      `/projets/QualiCheck/.gitea/workflows/` (`ci.yml`, `revue.yml`,
      `gate.yml`, `cd-staging.yml` — syntaxe GitHub Actions, transposable
      telle quelle) — garde bash
      `git tag --points-at "$SHA" | grep -q '^revue-ok/'`, pose de tag
      idempotente (skip si déjà posé), compte technique dédié + token
      restreint pour poser les tags (jamais le développeur),
      `fetch-depth: 0` sur tout job qui lit des tags. Déclenchement manuel
      du gate = tag `gate/<sha7>` poussé par le développeur (pas de
      `workflow_dispatch`), même logique que `revue-ok`/`eval-ok`. Revue finale
      de branche (2026-09-22) : corrections appliquées (xfail des 4 tests
      hors périmètre, réordonnancement gate-avant-push-image, commit du
      registre après publication, permissions `revue.yml`) — voir
      `MEMORY.md` et `CHANGELOG.md`. `ops/deploy.py::surveiller` et
      `app/gateway.py` restent hors périmètre (chantier 2).
- [x] **Conciliation architecture avant CI/CD (point 3)** : pas besoin de la
      rouvrir, l'architecture actée pour l'API (`docs/spec-v2.md` §4 — un seul
      artefact Docker partagé, 3 containers/rôles v1/v2/gateway, Caddy en
      frontal) sert aussi de cible pour le déploiement canary du point 3
      (confirmé par l'utilisateur, 2026-09-21).
- [x] **Périmètre exact du point 3, tranché (2026-09-22)** : point 3 =
      `llmops.yml` + `deploy.py::publier/deployer_canary/promouvoir/rollback`,
      **sans** `surveiller()`. `surveiller` (détection de dérive + rollback
      automatique) et `app/gateway.py` (routage réel du trafic canary)
      restent chantier 2. Conséquence : `test_promotion_canary_puis_totale`
      et `test_rollback_en_une_operation` (qui dépendent de `gateway.py`)
      resteront rouges tant que le chantier 2 n'est pas fait — attendu, pas
      un défaut du point 3.

## Chantier 2 — Pilotage

- [x] Squelette `ops/serveur_pilotage.py` : 6 routes du contrat gelé en 501,
      corps validés par les modèles Pydantic du contrat, `/health` pour le
      healthcheck (service compose `serveur_pilotage`, port hôte 8002)
- [x] Logique du serveur de pilotage implémentée (2026-09-23, TDD,
      `tests/unit/test_serveur_pilotage.py` réécrit) : les 6 routes lisent
      les métriques (via `ops/dashboard.py`), décident (dashboard, critère
      de promotion `canary.md`), écrivent le registre et journalisent —
      **en réutilisant `ops/registry/` existant**, pas de nouveau
      `ops/registre.json`/`ops/journal_pilotage.jsonl` (conflit de
      conception tranché, détail dans
      `docs/conception_revue/pilotage/formats-ops.md`, nouveau). Nouveau
      fichier `ops/regles_pilotage.json` pour les 4 seuils ajustables (`PUT
      /pilotage/regles/{signal}`, tracé au journal). Restent hors
      périmètre, documentés dans ce même fichier : régénération du
      Caddyfile (pas de container Caddy encore) et bouclage des règles
      ajustables sur la décision automatique de `ops.deploy.surveiller`.
- [x] **Arbitrage tranché (2026-09-22)** : pas de duplication à résoudre.
      `ops/dashboard.py::resume()` reste la fonction de calcul (imposée par
      le test d'acceptance fourni `test_dashboard_par_version`) ;
      `GET /pilotage/dashboard` (serveur de pilotage) réutilise cette même
      fonction en interne plutôt que de recalculer l'agrégation. Le service
      `dashboard` (8501, `--serve`) reste une vue texte/HTML autonome héritée
      de la remédiation, en plus de la route JSON contractuelle.
- [x] `ops/dashboard.py::resume/rendre_texte/rendre_html` implémentés
      (2026-09-23), fenêtre **temporelle** (`fenetre_s`, voir
      `docs/conception_revue/pilotage/fenetre-glissante-seuils.md`). Sans
      `metriques` explicite, `resume()` fusionne `METRICS_PATH` (v1) et
      `METRICS_PATH_V2` (v2, nouvelle variable, `docker-compose.yml` service
      `dashboard`) — condition pour que le trafic du container `v2` ne soit
      pas invisible du tableau de bord.
- [x] `app/gateway.py::choisir_version/etat/analyse` — routage canary
      (2026-09-23, TDD). `test_promotion_canary_puis_totale` et
      `test_rollback_en_une_operation` ne sont plus xfail.
- [x] `ops/deploy.py::surveiller` implémenté (2026-09-23, TDD) : dérive sur
      score/taux d'erreur/latence P95 (minimum de mesures requis), rollback
      automatique + journal. Fusion `ops/metrics.jsonl` +
      `ops/metrics_v2.jsonl` via `ops/dashboard.py::stores_metriques_par_defaut`
      (rendue publique, réutilisée). `test_journal_derive_et_rollback_automatique`
      n'est plus xfail — plus aucun test xfail dans
      `tests/acceptance/test_observabilite.py` (93 passed sur la suite
      complète).
- [ ] `docs/exploitation.md` — gabarit fourni à compléter (7 sections)

## Environnement

- [x] Environnement Docker démarré (`make up`), fournisseur Azure configuré
      (`.env`) — voir `ops/azure_adapter.py` pour l'adaptation nécessaire
      (api-version, max_tokens → max_completion_tokens)
- [x] Containers `v2` (8001) et `serveur_pilotage` (8002) ajoutés au
      `docker-compose.yml`, healthchecks Python sur `/health`, vérifiés avec
      `docker compose up -d --build --wait`
- [ ] Topologie cible complète de `docs/spec-v2.md` §4 : container v1 isolé,
      container gateway, Caddy en frontal — non entamée
- [x] Vérifier que les tests d'intégration v1 restent verts (`make test-integration`)
- [ ] `make test-acceptance` : 9 rouges / 1 vert au départ (`test_client_v1_fonctionne`),
      objectif = tout vert
