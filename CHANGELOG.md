# CHANGELOG — mardik-api-mlops

> Tracé horodaté, ordre inverse (plus récent en premier).

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
