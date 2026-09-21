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

- [ ] `models/v2/config.yaml` : stratégie `map_reduce_clauses`, prompt par
      section (titre + texte, sortie JSON contrainte), `schema_sortie`,
      température/seed pour un gate stable

## Chantier 1 — Le pipeline v2

- [ ] `app/pipeline/decoupage.py::decouper` — découpage par articles, taille
      cible 6 000 car., aucune perte de texte
- [ ] `app/pipeline/extraction.py::extraire` — un appel LLM par section
      (json_mode), gestion des réponses hors schéma sans planter
- [ ] `app/pipeline/consolidation.py::consolider` — fusion + dédoublonnage par
      type de clause
- [ ] `app/pipeline/confiance.py::scorer` — score composite (≥ 2 signaux
      indépendants ; conception : confiance LLM × stabilité inter-chunks)
- [ ] `app/api_v2.py::analyser_v2` + route `POST /v2/analyse` — orchestre les
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
- [ ] **Avant d'implémenter la CI/CD (point 3)** : session de conciliation
      conception ↔ code fourni dédiée, du même type que celle faite pour
      l'architecture v1/v2/gateway/Caddy (2026-09-21) — l'étape « déploiement
      canary » de `conception_figee/chantier1_llmops/img/chaine-llmops.png`
      suppose des artefacts/containers séparés par version, à confronter au
      `docker-compose.yml`/`Dockerfile` actuels avant d'écrire le workflow.
      Pas commencé, volontairement laissé de côté pendant le point 2 (API v2).

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
