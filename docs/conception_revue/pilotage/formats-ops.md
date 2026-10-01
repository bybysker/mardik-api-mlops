# Formats `registre` et `journal` de pilotage (révisé)

> Version révisée dans `mardik-api-mlops/docs/conception_revue/`, suite à
> l'implémentation du serveur de pilotage (`ops/serveur_pilotage.py`,
> 2026-09-23). Document original :
> `conception_figee/pilotage/formats-ops.md` (dépôt `mardik_nouvelle_version`,
> non modifié). Statut : décision révisée, pas provisoire — le code existant
> contraint le choix, comme pour `fenetre-glissante-seuils.md`.

## Le conflit

La conception d'origine prévoyait deux nouveaux fichiers, écrits uniquement
par le serveur de pilotage :

- `ops/registre.json` — objet unique `{v1: {fingerprint, pct}, v2:
  {fingerprint, etiquette, pct}}`, identifié par **fingerprint**
  (`SHA256(manifeste canonique)`) ;
- `ops/journal_pilotage.jsonl` — une ligne par décision, schéma
  `EntreeJournal` (`id/ts/signal/valeur/seuil/action/declencheur/
  fingerprint/nouvelle_repartition`).

Mais le chantier 1 avait déjà posé `ops/registry/` (classe `Registry`,
`ops/registry.py`) — `index.json` (`{active, canary, canary_percent,
precedente}`, identifié par **étiquette SemVer**, ex. `v2.0.0`) +
`journal.jsonl` (une ligne par événement, schéma `evenement/version/...`,
sans `signal`/`fingerprint`/`declencheur`). `app/gateway.py` (routage
canary, à chaque requête) et `ops/deploy.py` (`publier`/`deployer_canary`/
`promouvoir`/`rollback`/`surveiller`) sont déjà branchés dessus et testés.

## Décision (2026-09-23)

**Le serveur de pilotage réutilise `ops/registry/` tel quel** — pas de
nouveau fichier. Deux sources de vérité à synchroniser manuellement (la
gateway lisant l'une, le pilotage écrivant l'autre) auraient été plus
risquées qu'un écart de forme documenté.

Conséquences :

- **Identité par étiquette SemVer, pas par fingerprint.** `ops/registry/`
  ne clé jamais par fingerprint aujourd'hui ; `Bundle.empreinte()` existe
  mais n'est pas la clé du registre. Les réponses HTTP du serveur de
  pilotage utilisent le champ `fingerprint_cible`/`fingerprint` du contrat
  gelé, mais la valeur qu'il contient est en réalité l'étiquette SemVer
  (ex. `"v2.0.0"`), pas un SHA256.
- **v1/v2 au sens du contrat de pilotage = `v1.0.0` vs tout le reste.** Le
  registre peut contenir plusieurs versions v2 successives (patch
  auto-incrémenté à chaque build validé) ; `trafic.v1_pct`/`v2_pct` et
  `nouvelle_repartition` regroupent tout ce qui n'est pas `v1.0.0` sous
  « v2 », plutôt que de distinguer chaque étiquette.
- **Un seul journal.** `GET /pilotage/journal` reshape les entrées de
  `ops/registry/journal.jsonl` vers le schéma `EntreeJournal` : `action` ←
  `evenement`, `fingerprint` ← `version`, `declencheur` par défaut `"auto"`
  quand l'entrée n'en porte pas (seules les décisions déclenchées *via* le
  serveur de pilotage portent un `declencheur` explicite — `ops/deploy.py`
  accepte maintenant `**details` passés au journal pour ça).
- **`ops/regles_pilotage.json` (nouveau, seul vrai nouveau fichier)** :
  les 4 seuils ajustables (`latence_p95`, `taux_erreur`, `score_faible`,
  `canary`) n'existaient nulle part en tant qu'état persistant —
  `ops.deploy.surveiller` les prend en paramètres de fonction avec des
  valeurs par défaut, pas depuis un fichier. Seedé avec les valeurs du
  tableau de pilotage (`docs/conception_revue/pilotage/tableau-pilotage.md`).
  **Ces règles sont lues/écrites/tracées, mais pas encore bouclées sur la
  décision automatique** (`ops.deploy.surveiller` garde ses propres seuils
  par défaut) — ce câblage reste un point ouvert (voir `TODO.md`).

## Hors périmètre, non traité ici

- **Régénération du Caddyfile** : aucun container Caddy n'existe encore
  dans `docker-compose.yml` (topologie `docs/spec-v2.md` §4 non entamée
  au-delà de `v1`/`v2`/`serveur_pilotage` en ports distincts). Le serveur de
  pilotage ne régénère donc rien à ce stade.
- **Critère de promotion canary (`v2 ≥ v1`)** : implémenté dans
  `ops/serveur_pilotage.py::_evaluer_criteres_promotion` (contraintes
  client + jamais moins bonne + strictement meilleure sur au moins un
  signal, `canary.md` révisé), mais avec les valeurs de contrainte en dur
  (P95 < 8 s, coût < 0,15 €, erreur < 10 %) plutôt que lues depuis
  `ops/regles_pilotage.json` — même limite que ci-dessus.

## Écart à répercuter

Si `conception_figee/pilotage/formats-ops.md` (dépôt `mardik_nouvelle_version`)
est repris, y noter que `ops/registre.json` et `ops/journal_pilotage.jsonl`
n'ont jamais été créés — le rôle est tenu par `ops/registry/`.
