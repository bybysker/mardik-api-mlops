# Script de démo — v1 → v2 → pilotage

> Déroulé à suivre en présentant en direct. Les requêtes HTTP sont dans la
> collection Bruno `bruno/mardik-demo-cto/` (URLs en dur, `localhost`,
> aucun environnement à sélectionner) — chaque étape ci-dessous renvoie au
> numéro de requête correspondant. Durée indicative : 10–12 minutes.

## Avant de commencer

```bash
make up
```

Vérifier `.env` : `MOCK=off` signifie que **chaque appel v1/v2/gateway fait
un vrai appel LLM facturé** (Azure). C'est voulu pour une démo réelle, mais
à savoir avant de lancer.

Dans Bruno : ouvrir la collection `bruno/mardik-demo-cto/`. Ouvrir aussi
`http://localhost:8503` (client web de pilotage) dans un onglet à côté —
certaines étapes s'y regardent plutôt que dans Bruno.

**Vérifier l'état de départ** (sinon la démo raconte n'importe quoi) :

```bash
cat ops/registry/index.json   # attendu : active v1.0.0, canary null
```

Si `canary` n'est pas `null` ou si `active` n'est pas `v1.0.0`, c'est
qu'une démo précédente a laissé des traces : `uv run python -m ops.deploy
rollback --motif "remise à zéro démo"` puis revérifier.

---

## 1. v1 — le contrat historique, intouchable

**Dire** : « Voici l'API v1, celle qui tourne en production depuis le
début. Elle ne fait qu'une chose : découper le texte, l'envoyer en un seul
appel au LLM, et renvoyer une liste de clauses. Simple, mais avec un
défaut connu. »

**Faire** : requête Bruno **1. v1 — analyse**.

**Montrer** : la réponse contient `clauses` (une liste de libellés) et
`version: v1.0.0`. Pas de score de confiance — v1 ne sait pas dire si son
résultat est fiable.

**Dire** : « Le défaut qui a motivé ce projet : v1 tronque tout contrat au
delà de 16 000 caractères, *avant même* d'appeler le LLM. Sur un contrat
long, la fin est simplement absente de l'analyse — et rien ne le signale. »

## 2. v2 — un contrat long, et sans troncature

**Faire** : requête Bruno **2. v2 — analyse (contrat long, sans
troncature)**. Contrat de ~62 000 caractères, presque 4 fois la limite de
v1.

**Montrer**, dans la réponse :

- `sections` : le nombre d'articles découpés — v2 traite tout le texte,
  section par section ;
- `appels_llm` : un appel par section (aucune perte, contrairement à la
  troncature de v1) ;
- `confiance_globale` : un score composite (confiance du modèle ×
  stabilité entre sections) — absent de v1 ;
- `cout_eur` et `latence_ms` : à comparer aux contraintes client (coût
  < 0,15 €, P95 < 8 s).

**Dire** : « Contrat trop long pour v1, traité en entier par v2, avec un
score de confiance en plus — le juriste sait maintenant *quand* faire
confiance au résultat, pas seulement lire une liste plate. »

**Variante terminal** (pour rejouer avec un autre contrat sans toucher à
Bruno — `c10.txt` et `c12.txt` sont encore plus longs) :

```bash
jq -Rs '{texte: .}' eval/contrats/c12.txt | \
  curl -s -X POST http://localhost:8001/v2/analyse \
    -H "Content-Type: application/json" -d @- | jq
```

## 3. Publier v2 et déployer un canary (terminal)

Pas d'endpoint HTTP pour publier une version — c'est la chaîne CI/CD qui le
fait en conditions réelles (`.github/workflows/cd-main.yml`). Pour la démo,
en accéléré :

```bash
uv run python -c "
from app.llm_client import Bundle
from ops.deploy import deployer_canary, prochaine_version
from ops.registry import Registry

registry = Registry()
version = prochaine_version('patch', registry=registry)
print('version :', version)
registry.etiqueter(version, Bundle.charger('v2'), commit='demo', note_eval=0.9)
print(deployer_canary(version, pourcentage=20, registry=registry))
"
```

**Dire** : « En réalité cette étiquette vient d'un gate d'évaluation réel
(micro-F1 sur 12 contrats, seuils 0,75/0,80) — ici je saute cette étape
pour la démo, la note 0,9 est fictive. » (Le gate réel coûte de l'argent à
chaque run, pas à faire en direct devant un CTO sans prévenir.)

**Faire** : requête Bruno **3. Gateway — état**. `canary` doit maintenant
afficher la version qu'on vient de déployer, à 20 %.

**Dire** : « Ce changement a pris effet sans redémarrer aucun service — la
gateway relit ce fichier à chaque requête. »

## 4. La gateway mélange le trafic

**Faire** : requête Bruno **4. Gateway — analyse**, rejouée 5 à 10 fois
(bouton « Send » plusieurs fois, ou Bruno Runner sur cette requête).

**Montrer** : l'en-tête de réponse `X-Mardik-Version` change d'une requête
à l'autre — environ 1 fois sur 5 la v2, le reste en v1, conforme au
pourcentage canary.

**Dire** : « C'est exactement le trafic que verrait le client final —
mélangé, sans qu'il s'en aperçoive, pendant qu'on observe si la v2 tient
ses promesses. »

## 5. Le tableau de bord de pilotage

**Faire** : ouvrir `http://localhost:8503` (tableau de bord) — ou requête
Bruno **5. Pilotage — tableau de bord** pour voir le JSON brut derrière.

**Montrer** : latence P95, coût moyen, taux d'erreur, répartition v1/v2,
et la distribution du score de confiance (proportion de scores faibles).

**Dire** : « C'est le même écran que le client verrait en observabilité —
et c'est cette même API que consulte le mécanisme de décision automatique
qu'on va voir dans un instant. »

## 6. Le tableau de pilotage (règles)

**Faire** : onglet « Pilotage » du client web, ou requête Bruno
**6. Pilotage — règles**.

**Montrer** : les 4 signaux surveillés (latence P95 > 8 s, taux d'erreur
> 10 %, score faible > 20 %, canary conforme), chacun avec sa rétroaction
et si c'est déclenché automatiquement ou nécessite un humain.

**Dire** : « Ces seuils sont ajustables en direct — bouton « Modifier »,
sans redéploiement — et chaque ajustement est tracé, on va le voir au
journal. »

## 7. Promotion (humain, via le critère v2 ≥ v1)

**Faire** : onglet « Actions » du client web (bouton « Promouvoir », palier
50 %), ou requête Bruno **7. Pilotage — promotion**.

**Deux issues possibles, les deux sont pédagogiques** :

- **200** : la v2 est promue à 50 % — le critère (contraintes client + v2
  jamais moins bonne + strictement meilleure sur au moins un signal) est
  tenu.
- **409** : refusé, avec le motif exact dans la réponse (ex. pas assez de
  mesures sur la fenêtre, ou un signal où v2 n'est pas meilleure). **Dire** :
  « C'est voulu — le système refuse de promouvoir sans preuve, même si on
  clique. »

## 8. Rollback immédiat

**Faire** : onglet « Actions » (bouton « Rollback immédiat »), ou requête
Bruno **8. Pilotage — rollback**.

**Montrer** : rejouer **3. Gateway — état** — `canary: null`, 100 % du
trafic repasse sur la version saine, sans redémarrage.

**Dire** : « Une opération, pas une procédure à plusieurs étapes. C'est la
promesse du brief : plus jamais un déploiement raté qui reste en
production. »

> **Après cette étape, v1 sert 100 % du trafic** — donc rejouer la requête
> 4 redonne des réponses v1, tronquées sur les contrats longs. C'est le
> résultat attendu d'un rollback, pas une panne. Pour remontrer v2, il faut
> refaire l'étape 3 (déployer un canary).

## 9. Le journal — tout est tracé

**Faire** : onglet « Journal » du client web, ou requête Bruno
**9. Pilotage — journal**.

**Montrer** : la séquence complète de la démo — canary, promotion (ou
refus), rollback — chacune avec date, signal, déclencheur (auto/humain).

**Dire** : « Qui, quand, pourquoi — pour chaque décision, humaine ou
automatique. C'est ce document qu'on relit à 3 h du matin si ça dérive »
(clin d'œil à `docs/exploitation.md`).

---

## Si quelque chose ne répond pas

- `make up` puis attendre ~10 s (healthchecks).
- `docker compose logs <service>` pour le détail.
- Vérifier `.env` (`MOCK`, secrets Azure) si les appels v1/v2 échouent en
  503.

## Pour aller plus loin (hors script, si le temps le permet)

- **Dérive automatique** : `make traffic MODE=derive-score` (nécessite
  `MOCK=off`) fait chuter les scores en production ; `ops.deploy.surveiller`
  (pas encore bouclé automatiquement, voir `docs/exploitation.md` §6)
  détecterait et déclencherait seul un rollback — à montrer en CLI plutôt
  qu'en live si le temps manque, voir `docs/exploitation.md` §7 pour un
  transcript déjà capturé.
