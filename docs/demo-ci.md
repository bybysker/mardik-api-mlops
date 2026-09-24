# Script de démo — la chaîne CI/CD (de `feature/x` au canary)

> Déroulé à suivre en présentant en direct. On fait parcourir à un petit
> changement toute la chaîne : `feature/x` → PR → revue → `dev` → gate →
> `main` → canary. Chaque étape dit **quelle commande taper**, **quel
> workflow se déclenche** et **ce qu'il faut montrer**. Référence complète
> : `docs/exploitation.md` § 2 et § 3. Durée indicative : 20–25 minutes
> (surtout de l'attente de runners, voir « Temps morts » en fin de page).

## Vue d'ensemble

| # | Geste du développeur | Workflow déclenché | Coût LLM | Résultat |
|---|---|---|---|---|
| 1 | `git push` sur `feature/x` | `ci.yml` (+ `alerte-eval.yml` si chemin sensible) | 0 (ou payant pour l'alerte) | lot A vert/rouge |
| 2 | approbation de la PR par `connarddu16-design` | `revue.yml` | 0 | tag `revue-ok/<sha7>` |
| 3 | `git merge --ff-only` vers `dev` + push | `ci.yml` | 0 | — |
| 4 | `git push origin gate/<sha7>` | `gate.yml` | **payant** | tag `eval-ok/<sha7>` |
| 5 | `git merge --ff-only` vers `main` + push | `cd-main.yml` | **payant** | version publiée, image `ghcr.io`, canary 10 % |

Deux idées à faire passer pendant toute la démo :

1. **Les preuves sont des tags posés sur un SHA.** `revue-ok` dit « ce code
   exact a été relu, et son lot A est vert ». `eval-ok` dit « ce code exact
   a passé l'évaluation réelle ». Un SHA différent = plus de preuve.
2. **Le moins cher d'abord.** Rien de payant n'est lancé tant que ce qui
   est gratuit (lint, tests mockés, revue) n'est pas passé.

## Avant de commencer

Hypothèses (à vérifier, la démo échoue sinon) :

- `gh` est installé et authentifié sur le compte développeur
  (`wawawaformation`) : `gh auth status`.
- On a accès au compte relecteur **`connarddu16-design`** (navigateur en
  navigation privée, ou `gh auth login` sur ce second compte) — c'est le
  seul dont l'approbation pose `revue-ok` (`revue.yml`).
- Les secrets du dépôt existent : `AZURE_*` (évaluation réelle) et
  `CI_TAG_TOKEN` (pose des tags). Vérifier : `gh secret list`.

**Vérifier l'état de départ** :

```bash
git fetch --all --tags
git status                        # arbre propre
git log --oneline -1 origin/dev
git merge-base --is-ancestor origin/main origin/dev && echo ok
                                  # main doit être ancêtre de dev, sinon le ff-only final échoue
cat ops/registry/index.json       # attendu : active v1.0.0, canary null
```

**Coût** : les étapes 4 et 5 appellent le vrai modèle Azure (12 contrats
d'évaluation chacune). L'étape 1 aussi **si** le changement touche
`models/*/config.yaml`, `app/pipeline/**`, `app/llm_client.py` ou `eval/**`.

Dans le navigateur : ouvrir l'onglet **Actions** du dépôt
(`gh repo view --web`, puis *Actions*). Dans un terminal à part, garder
sous la main :

```bash
gh run list --limit 5     # les dernières exécutions
gh run watch              # suivre une exécution en direct (choix interactif)
```

---

## 0. En local — la CI avant la CI

**Dire** : « Avant de pousser quoi que ce soit, le développeur peut jouer
exactement le lot A chez lui. Même commandes que le workflow, LLM mocké. »

**Faire** :

```bash
make ci
```

**Ce que ça fait** : `ruff check .`, puis `pytest` sur `tests/unit`,
`tests/integration`, `tests/acceptance` avec `MOCK=on` — les réponses LLM
viennent des fixtures enregistrées dans `eval/fixtures/`, **aucun appel
payant**.

**Montrer** : tout vert en quelques secondes. « Si c'est rouge ici, ça
sera rouge sur GitHub : inutile de pousser. »

## 1. Push sur `feature/x` — le lot A (`ci.yml`)

**Faire** : créer la branche et un changement **anodin** (hors chemins
sensibles, pour ne pas payer l'alerte) :

```bash
git checkout dev && git pull
git checkout -b feature/demo-ci
echo "- démo CI du $(date +%F)" >> docs/demo-ci-trace.md
git add docs/demo-ci-trace.md
git commit -m "docs: trace the CI demo run"
git push -u origin feature/demo-ci
gh run list --limit 3
```

**Ce que ça fait** : `ci.yml` se déclenche sur **tout push de branche sauf
`main`**. Un runner Ubuntu installe `uv`, fait `uv sync`, puis lint + les
trois niveaux de tests en `MOCK=on`. Permissions : lecture seule.

**Montrer** : l'exécution *CI* dans l'onglet Actions, les deux étapes
*Linting* et *Tests*. « C'est le gate le plus fréquent et le moins cher. »

**Variante — l'alerte d'évaluation (`alerte-eval.yml`)**, si on veut la
montrer (payant) : faire en plus un changement neutre dans un chemin
sensible, par ex. un commentaire dans `models/v2/config.yaml`, puis pousser.
Un **second** workflow part : il démarre le proxy + l'adaptateur Azure en
Docker et lance `eval.run_eval --version v2 --seuil 0.75` sur le vrai
modèle. **Montrer** l'onglet *Summary* du run : « Alerte évaluation —
signal, pas preuve. Aucun tag posé. » **Dire** : « Le développeur est
prévenu tôt que sa modif fait bouger la note. Mais ça ne prouve rien : ce
workflow n'a même pas le droit d'écrire dans le dépôt. La preuve viendra
après la revue. »

## 2. La PR et la revue (`revue.yml`)

**Faire** (compte développeur) :

```bash
gh pr create --base dev --head feature/demo-ci \
  --title "docs: trace the CI demo run" --body "Démo de la chaîne CI."
```

Puis, **connecté en `connarddu16-design`**, approuver la PR (onglet *Files
changed* → *Review changes* → *Approve*), ou en CLI sur ce compte :

```bash
gh pr review --approve <numéro-de-PR>
```

**Ce que ça fait** : `revue.yml` se déclenche sur `pull_request_review`.
Il ne fait quelque chose que si les trois conditions sont vraies :
approbation, par `connarddu16-design`, sur une PR vers `dev`. Il **attend
ensuite que `ci.yml` ait conclu `success` sur le SHA de tête** (jusqu'à
10 min, en interrogeant l'API Actions), puis pose `revue-ok/<sha7>`.

**Montrer** :

```bash
git fetch --tags
git tag --points-at HEAD          # revue-ok/<sha7>
```

Et dans les logs du run : `[ok] lot A vert sur <sha>` puis
`[ok] revue-ok/<sha7> posé`.

**Dire** : « Pourquoi un second compte ? GitHub interdit d'approuver sa
propre PR. Ce compte n'est pas une deuxième personne, c'est un mécanisme de
fraîcheur : l'approbation porte sur *ce* SHA-là. »

## 3. Fusion fast-forward vers `dev`

**Faire** :

```bash
git checkout dev
git merge --ff-only feature/demo-ci
git push origin dev
```

**Ce que ça fait** : `dev` avance **sur le même SHA** que celui relu — le
tag `revue-ok` reste valable. `ci.yml` rejoue sur `dev` (gratuit). La PR se
ferme toute seule.

**Dire** — point clé de la démo : « Jamais les boutons de fusion de
GitHub. *Merge commit*, *Squash*, *Rebase* : les trois fabriquent un
nouveau SHA, que les tags ne suivent pas. Le gate refuserait — c'est
arrivé pour de vrai avec la PR #1. `--ff-only` refuse au lieu de fabriquer
un commit de fusion en silence. »

## 4. Le gate (`gate.yml`) — et son refus

**Montrer d'abord le refus (gratuit, très parlant)** : poser un tag
`gate/` sur un commit **sans** `revue-ok`, par ex. un commit local jetable :

```bash
git checkout -b demo-refus
git commit --allow-empty -m "chore: commit without review"
git tag "gate/$(git rev-parse --short=7 HEAD)"
git push origin "gate/$(git rev-parse --short=7 HEAD)"
```

**Montrer** : le job échoue à la **première** étape —
`[refus] aucun tag revue-ok/* ne pointe sur <sha>`. **Dire** : « Zéro
appel payant tant que la revue n'est pas fraîche. »

Nettoyer :

```bash
git push origin --delete "gate/$(git rev-parse --short=7 HEAD)"
git tag -d "gate/$(git rev-parse --short=7 HEAD)"
git checkout dev && git branch -D demo-refus
git push origin --delete demo-refus 2>/dev/null   # si la branche a été poussée
```

**Puis le cas nominal** (payant), sur `dev` :

```bash
git checkout dev
SHA7=$(git rev-parse --short=7 HEAD)
git tag "gate/$SHA7"
git push origin "gate/$SHA7"
gh run watch
```

**Ce que ça fait** — deux jobs enchaînés par `needs:` :

1. **`tests`** : vérifie `revue-ok` sur ce SHA, puis rejoue lint + tests
   mockés. Répétition voulue : « dans `ci.yml` ils informent, ici ils
   prouvent ».
2. **`evaluation`** (seulement si `tests` est vert) : démarre proxy +
   adaptateur Azure, lance l'**évaluation réelle** (`v2`, seuil 0,75),
   publie `eval/history.jsonl` en artefact, puis pose `eval-ok/<sha7>`.

**Montrer** : le graphe des deux jobs dans Actions, le score dans les logs
de l'évaluation, l'artefact téléchargeable, puis :

```bash
git fetch --tags
git tag --points-at HEAD          # revue-ok/<sha7>, gate/<sha7>, eval-ok/<sha7>
```

**Dire** : « Deux tags distincts : `gate/` est un déclencheur, on peut le
recréer. `eval-ok/` est une preuve, immuable — elle n'existe que si tout
est vert. »

## 5. Fusion vers `main` — le déploiement (`cd-main.yml`)

**Faire** :

```bash
git checkout main
git merge --ff-only dev
git push origin main
gh run watch
```

**Ce que ça fait**, dans l'ordre :

1. Vérifie que le SHA poussé porte **les deux** tags `revue-ok` et
   `eval-ok` — sinon refus.
2. Calcule la prochaine version SemVer : `patch` par défaut, `minor` ou
   `major` si le message du commit de tête contient `[minor]`/`[major]`
   (`ops/deploy.py::prochaine_version`).
3. `ops.deploy publier` : **rejoue l'évaluation réelle** (simplification
   assumée, le CLI ne sait pas réutiliser le rapport du gate) et étiquette
   la version dans le registre `ops/registry/`.
4. Committe `ops/registry/<version>/` et le pousse sur `main`
   (compte `mardik-ci`).
5. Construit l'image Docker et la pousse sur
   `ghcr.io/wawawaformation/mardik-api-mlops:<version>`.
6. `ops.deploy canary <version>` : la nouvelle version reçoit **10 %** du
   trafic.

**Montrer** :

```bash
git pull origin main
git log --oneline -2              # chore(registry): publish vX.Y.Z
ls ops/registry/                  # le dossier de la nouvelle version
```

Et, dans les logs de la dernière étape, l'état renvoyé par `canary`
(`'canary': 'vX.Y.Z', 'canary_percent': 10`). Attention :
`ops/registry/index.json` n'est **pas** committé par le workflow — l'état
du canary vit sur le runner, pas dans le dépôt. Et la page *Packages* du dépôt GitHub avec l'image taguée.

**Dire** : « Ici s'arrête l'automatique. Pas de promotion ni de rollback
automatiques dans cette chaîne : c'est le pilotage (`ops.deploy
surveiller`, `promouvoir`, `rollback`), montré dans
`docs/demo-v1-v2-pilotage.md`. »

---

## Temps morts et parades

- **Attente des runners** (1–3 min par workflow) : en profiter pour
  ouvrir le YAML correspondant dans `.github/workflows/` et lire les
  commentaires d'en-tête, qui disent le *pourquoi* de chaque garde.
- **`revue.yml` en `[attente]`** : normal si `ci.yml` n'a pas fini, il
  réessaie toutes les 20 s.
- **Enregistrer à l'avance** : pour une démo sans risque, jouer la chaîne
  la veille et montrer les exécutions déjà terminées dans Actions (elles
  restent consultables), en ne rejouant en direct que les étapes 0, 1 et le
  refus de l'étape 4 — toutes gratuites.

## Après la démo

- `main` a **un commit de plus** que `dev` (`chore(registry): publish …`).
  Réaligner avant la prochaine fusion ff-only :

  ```bash
  git checkout dev && git merge --ff-only origin/main && git push origin dev
  ```

- Le dossier `ops/registry/<version>/` reste dans l'historique de `main`
  (voulu : c'est la trace de la publication). `index.json` n'ayant pas été
  committé, l'état local reste `active v1.0.0, canary null`.
- Supprimer la branche de démo :
  `git push origin --delete feature/demo-ci && git branch -d feature/demo-ci`.
