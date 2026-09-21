# Analyse de cohérence : conception vs. code source

> Document de travail. Objectif : vérifier, avant implémentation, que les
> décisions actées dans le dossier de conception (dépôt parent
> `mardik_nouvelle_version/conception/`) correspondent bien à ce que le code
> source fourni ici impose ou suggère. Rédigé après lecture de `README.md`,
> `docs/besoin_client.md`, `docs/schema_remediation.md`, `app/api_v1.py`,
> `app/api_v2.py`, `app/gateway.py`, `app/telemetry.py`,
> `app/pipeline/decoupage.py`, `app/pipeline/confiance.py`,
> `models/v1/config.yaml`, `models/v2/config.yaml`, `eval/run_eval.py`,
> `ops/deploy.py`, `.github/workflows/llmops.yml`, `Makefile`,
> `tests/acceptance/test_chaine.py`, `tests/acceptance/test_observabilite.py`.

## Points cohérents (aucune action requise)

- **Besoin client** (`docs/besoin_client.md`) : identique au brief déjà connu
  (contrats longs tronqués, score de confiance, P95 < 8 s, coût < 0,15 €,
  ~400 contrats/mois, rollback immédiat).
- **Télémétrie** (`app/telemetry.py`, `docs/schema_remediation.md`) :
  `Mesure`, `MetricsStore` → `ops/metrics.jsonl`, traces OpenTelemetry
  (`analyse.requete` → `llm.appel`), logs structurés — correspond exactement
  à ce que la conception suppose déjà acquis.
- **`/v1/analyse` intouchable** (`app/api_v1.py`) : confirmé, troncature à
  `contexte_max_caracteres` (16 000 car.) bien la cause du défaut documentée.
- **Bundle v2** (`models/v2/config.yaml`) : `contexte_max_caracteres: 6000`
  par section — conforme à la taille cible du découpage
  (`conception/chantier1_llmops/decoupage-chunking.md`).
- **Score de confiance** (`app/pipeline/confiance.py`, stub) : exige « au
  moins deux signaux indépendants » ; notre décision (confiance LLM ×
  stabilité inter-chunks, `conception/chantier1_llmops/score-confiance.md`)
  satisfait cette exigence sans contradiction.
- **Découpage** (`app/pipeline/decoupage.py`, stub) : découpage par articles,
  taille cible 6000 car. — conforme à `decoupage-chunking.md`. Le
  chevauchement (~250 car.) n'est pas imposé par le stub : notre choix reste
  valable.
- **Gateway et canary** (`app/gateway.py`) : routage canary par pourcentage,
  bundle lu depuis le registre à chaque requête — conforme à
  `conception/pilotage/canary.md`.
- **Versionnage** (`ops/deploy.py::publier`, stub) : joue le gate
  d'évaluation puis étiquette dans le registre, refuse si le gate échoue —
  conforme à la décision « incrément du patch au build validé, jamais à la
  fusion » (`docs/versionnage.md`).

## Point de conflit ouvert — fenêtre glissante (comptage vs. temporelle)

**Décision actée** (`conception/pilotage/fenetre-glissante-seuils.md`) :
fenêtre **en nombre de requêtes** (50 dernières, minimum 30 avant décision),
en écartant explicitement une fenêtre temporelle : *« le volume est faible
(~400 contrats/mois ≈ 13/jour) ; une fenêtre temporelle contiendrait très peu
de requêtes et serait trop sensible au hasard »*.

**Ce qu'impose le code fourni** : les tests d'acceptance, figés, appellent :

```python
# tests/acceptance/test_observabilite.py
ops.deploy.surveiller(registry, metriques, fenetre_s=60, score_min=0.7, minimum=10)
ops.dashboard.resume(metriques, fenetre_s=60, registry=registry)
```

Le paramètre `fenetre_s` (secondes) impose une fenêtre **temporelle**, pas un
comptage de requêtes. `minimum` reste un garde-fou anti-faux-positifs (comme
prévu dans la conception), mais la dimension principale de la fenêtre est le
temps, pas le nombre.

**Conséquence** : ces tests n'étant pas modifiables, l'implémentation de
`ops.deploy.surveiller` et `ops.dashboard.resume` devra être temporelle,
contredisant la décision actée et présentée dans le dossier de conception.

**Statut : non tranché, volontairement laissé ouvert** (choix de
l'utilisateur, 2026-09-21). Options envisagées à ce stade, à retrancher plus
tard (chantier 2, calibration des seuils) :

1. Réviser `fenetre-glissante-seuils.md` pour adopter une fenêtre
   temporelle, en cohérence avec l'interface imposée par le code.
2. Solution hybride : conserver `fenetre_s` comme paramètre d'interface
   (pour les tests) mais plafonner en interne à N=50 dernières mesures dans
   cette fenêtre.

## Points mineurs sans action (à garder en tête)

- **Formule de la note d'évaluation** : `eval/run_eval.py` (stub) décrit la
  note comme un « rappel » (recall) moyen, alors que
  `conception/chantier1_llmops/note-evaluation.md` a décidé un micro-F1
  scindé courts/longs. Aucun test ne verrouille la formule exacte (seuls les
  seuils et comparaisons v1/v2 sont testés), et le champ `seuil_note` par
  contrat permet toujours d'implémenter le split courts/longs (9 courts ≥
  0,75, 3 longs ≥ 0,80). Le micro-F1 reste donc implémentable tel quel.
- **`.github/workflows/llmops.yml`** : n'est qu'un squelette `[TEMPLATE]`
  (déclenché sur `push main`, `pull_request`, tags — pas de branche `dev`).
  À réécrire au moment de l'implémentation pour refléter le mécanisme à deux
  tags (`revue-ok/<sha>`, `eval-ok/<sha>`) décrit dans
  `conception/chantier1_llmops/gel-eval-avant-fusion.md`.
- **Codes d'erreur `/v2/analyse`** : le stub `app/api_v2.py` ne documente que
  422 et 503 (pas de 413 pour un document trop long). Aucun test ne
  l'exige ni ne l'interdit : le garde-fou des 250 000 caractères
  (`conception/chantier1_llmops/decoupage-chunking.md`) reste ajoutable sans
  conflit.
