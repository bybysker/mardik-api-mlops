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

## En attente de décision utilisateur

- [ ] Committer les fichiers en attente (`git status` : `docs/analyse-coherence-conception.md`
      modifié, `docs/conception_revue/` et `docs/img/` nouveaux) — pas encore
      committé, accord explicite requis avant chaque commit

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

- [ ] Revoir si `CANARY_PERCENT` et `MOCK` doivent rester des valeurs par
      défaut dans `.env`, ou si `CANARY_PERCENT` doit plutôt être piloté
      dynamiquement (registre / `ops/deploy.py --pourcentage`) plutôt qu'un
      défaut statique — point soulevé en nettoyant `.env` (2026-09-21)
- [ ] `ops/deploy.py::publier/deployer_canary/promouvoir/rollback/surveiller`
- [ ] `ops/dashboard.py::resume/rendre_texte/rendre_html` — fenêtre
      **temporelle** (`fenetre_s`), voir `docs/conception_revue/pilotage/fenetre-glissante-seuils.md`
- [ ] `.github/workflows/llmops.yml` — actuellement un `[TEMPLATE]` générique
      (push `main`/PR/tags) ; à réécrire pour le mécanisme à deux tags
      (`revue-ok/<sha>`, `eval-ok/<sha>`) décrit dans
      `conception_figee/chantier1_llmops/gel-eval-avant-fusion.md`
- [x] **Conciliation architecture avant CI/CD (point 3)** : pas besoin de la
      rouvrir, l'architecture actée pour l'API (`docs/spec-v2.md` §4 — un seul
      artefact Docker partagé, 3 containers/rôles v1/v2/gateway, Caddy en
      frontal) sert aussi de cible pour le déploiement canary du point 3
      (confirmé par l'utilisateur, 2026-09-21).
- [ ] **Point ouvert, à trancher au démarrage de la prochaine session** :
      périmètre exact du point 3. `ops/deploy.py` (stub fourni) contient
      `publier/deployer_canary/promouvoir/rollback` (mécanique de
      déploiement, clairement point 3) **et** `surveiller` (détection de
      dérive + rollback automatique) qui ressemble à la boucle « rollback sur
      signal » du chantier 2 du brief. `app/gateway.py` (routage réel du
      trafic canary, testé par `test_promotion_canary_puis_totale` et
      `test_rollback_en_une_operation`) est rangé sous chantier 2 dans ce
      TODO, mais sans lui la mécanique de canary ne route aucun trafic pour
      de vrai — ces deux tests fournis resteront rouges tant que le choix
      n'est pas fait. Question posée à l'utilisateur, pas encore répondue :
      point 3 = `llmops.yml` + `deploy.py` sans `surveiller()` (recommandé),
      ou avec `surveiller()`, ou avec `gateway.py` en plus.

## Chantier 2 — Pilotage

- [ ] `app/gateway.py::choisir_version/etat/analyse` — routage canary
- [ ] `docs/exploitation.md` — gabarit fourni à compléter (7 sections)

## Environnement

- [x] Environnement Docker démarré (`make up`), fournisseur Azure configuré
      (`.env`) — voir `ops/azure_adapter.py` pour l'adaptation nécessaire
      (api-version, max_tokens → max_completion_tokens)
- [x] Vérifier que les tests d'intégration v1 restent verts (`make test-integration`)
- [ ] `make test-acceptance` : 9 rouges / 1 vert au départ (`test_client_v1_fonctionne`),
      objectif = tout vert
