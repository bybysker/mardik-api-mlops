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

- [ ] `eval/run_eval.py::evaluer` — note par version (formule libre tant que
      les seuils/comparaisons testés passent ; conception : micro-F1 scindé
      courts/longs via `seuil_note` par contrat), latence P95, coût moyen

## Chantier 1 — La chaîne LLMOps

- [ ] **Exécution en cours (2026-09-22), en pause** : plan à 8 tâches
      (`docs/superpowers/plans/2026-09-22-chaine-llmops.md`), dans un worktree
      isolé (`.worktrees/chaine-llmops/`, branche `sdd/chaine-llmops`, pas
      encore fusionnée). Tâche 1/8 faite et revue (`ops.deploy.prochaine_version`).
      Reprendre à la tâche 2 (`eval.run_eval.evaluer`). Détail : `MEMORY.md`
      (« En cours »).
- [x] **Tranché (2026-09-22)** : `CANARY_PERCENT` et `MOCK` restent des
      valeurs par défaut statiques dans `.env`. Le pilotage dynamique du
      pourcentage canary relève du chantier 2 (registre/serveur de
      pilotage), pas de l'environnement de base.
- [ ] `ops/deploy.py::publier/deployer_canary/promouvoir/rollback` (point 3 ;
      `surveiller` reste chantier 2, voir décision périmètre ci-dessus)
- [ ] `ops/dashboard.py::resume/rendre_texte/rendre_html` — fenêtre
      **temporelle** (`fenetre_s`), voir `docs/conception_revue/pilotage/fenetre-glissante-seuils.md`
- [ ] `.github/workflows/llmops.yml` — actuellement un `[TEMPLATE]` générique
      (push `main`/PR/tags) ; à réécrire pour le mécanisme à deux tags
      (`revue-ok/<sha>`, `eval-ok/<sha>`) décrit dans
      `conception_figee/chantier1_llmops/gel-eval-avant-fusion.md`. **Exemple
      à suivre (tranché 2026-09-22)** : même principe de gates que
      `/projets/QualiCheck/.gitea/workflows/` (`ci.yml`, `revue.yml`,
      `gate.yml`, `cd-staging.yml` — syntaxe GitHub Actions, transposable
      telle quelle) — 4 workflows séparés par rôle, garde bash
      `git tag --points-at "$SHA" | grep -q '^revue-ok/'`, pose de tag
      idempotente (skip si déjà posé), compte technique dédié + token
      restreint pour poser les tags (jamais le développeur),
      `fetch-depth: 0` sur tout job qui lit des tags. **Déclenchement manuel
      du gate = tag `gate/<sha7>` poussé par le développeur** (pas de
      `workflow_dispatch`), même logique que `revue-ok`/`eval-ok`.
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
- [ ] Logique du serveur de pilotage : lecture de `ops/metrics.jsonl`,
      décisions (fenêtre 120 s / 300 s, minimum 10 mesures — voir
      `docs/conception_revue/pilotage/fenetre-glissante-seuils.md`), écriture
      du registre et de `ops/journal_pilotage.jsonl`, régénération du Caddyfile
- [x] **Arbitrage tranché (2026-09-22)** : pas de duplication à résoudre.
      `ops/dashboard.py::resume()` reste la fonction de calcul (imposée par
      le test d'acceptance fourni `test_dashboard_par_version`) ;
      `GET /pilotage/dashboard` (serveur de pilotage) réutilise cette même
      fonction en interne plutôt que de recalculer l'agrégation. Le service
      `dashboard` (8501, `--serve`) reste une vue texte/HTML autonome héritée
      de la remédiation, en plus de la route JSON contractuelle.
- [ ] Faire lire `ops/metrics_v2.jsonl` (service `v2`) par `ops/dashboard.py`
      et `ops/deploy.py::surveiller`, qui ne connaissent que
      `ops/metrics.jsonl` — condition pour que le trafic du container `v2`
      soit visible dans la surveillance
- [ ] `app/gateway.py::choisir_version/etat/analyse` — routage canary
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
