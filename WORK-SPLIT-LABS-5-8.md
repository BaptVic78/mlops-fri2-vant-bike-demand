# Répartition Labs 5 à 8

Fichier pour l'équipe vant. Une personne donne ce fichier à son assistant avec son
nom et un numéro de lab. L'assistant ne fait que cette partie.

Cours : https://github.com/minhtc-uca/mlops-course
Dépôt : https://github.com/BaptVic78/mlops-fri2-vant-bike-demand
Les Labs 3 et 4 sont déjà sur `main`.

| Nom | GitHub |
|---|---|
| Victor Rouleau | `BaptVic78` |
| Nils Giraud | `nilsgrd` |
| Axel Alacache | `axou947` |
| Thomas Soubagne | `thomassbgn` |

## Consigne pour l'assistant

La personne te donne son nom et `Lab 5`, `Lab 6`, `Lab 7` ou `Lab 8`.
Tu réalises uniquement la ligne dont elle est owner. Tu ne codes pas les
parties des autres. Tu ouvres une seule pull request, depuis `main`, sur une
branche à toi. Un autre membre, nommé ci-dessous, la relit avant le merge.

Avant de coder, lis le PDF du lab dans
`slides/week03` ou `slides/week04` du dépôt du cours. Les choix de conception
vont dans le README : le choix retenu, l'option écartée, et pourquoi.

Règles communes :

- Petits changements. Ne pas affaiblir un test, le sauter, ni relâcher une assertion.
- `uv sync --locked` et `uv run --locked`. Ne pas régénérer `uv.lock` pour faire passer un check. Une nouvelle dépendance se déclare dans `pyproject.toml`, puis le lock est mis à jour.
- Ne pas committer `.venv/`, `artifacts/`, `tracking/`, un secret, ni un rapport individuel.
- Ne pas calculer de métrique sur les lignes de test de juillet–décembre 2012.
- Le service ne réentraîne pas au démarrage ni pendant une requête.
- Les preuves sont les commandes, le commit, et le résultat observé. Ne pas inventer un run vert.
- Le rapport d'équipe du lab va dans ce dépôt. Le rapport personnel (`reports/week-3.md` ou `reports/week-4.md`) va dans le dépôt privé de la personne, pas ici.

## Lab 5 — service, logs, identité du modèle

Prérequis : Lab 4 sur `main`. PDF : `Week 3 — Lab 5`.
Trois résultats : le service part de l'image, chaque requête écrit une ligne de log, un script hors du conteneur vérifie le modèle et le code.

| Partie | Owner | Relu par |
|---|---|---|
| Démarrage | Victor Rouleau | Nils Giraud |
| Logs | Nils Giraud | Thomas Soubagne |
| Vérification extérieure | Axel Alacache | Victor Rouleau |
| README Deploy | Thomas Soubagne | Axel Alacache |

### Victor Rouleau — démarrage

Étendre le `Dockerfile` du Lab 4 pour que le service démarre avec des réglages passés au `docker run` (`-e`, port publié seulement sur `127.0.0.1`). Écrire dans le README ce que « deployed » veut dire et qui lance la vérification finale. Répondre aux questions : quels réglages changent entre le laptop et le conteneur, d'où vient le modèle au démarrage, quand le service est « ready », que dit-il si le modèle manque.

Fini quand un camarade peut démarrer le conteneur en suivant seulement le README, et que `/health` et `/predict` répondent comme au Lab 4.

### Nils Giraud — logs

Une ligne de log par requête, lisible avec `docker logs` sans revoir la requête. On doit pouvoir y distinguer une requête acceptée et une requête rejetée, le statut, la durée, et l'identité du modèle. Décider et documenter ce qui ne doit jamais apparaître dans un log. Ne pas retirer les champs déjà renvoyés par l'API.

Fini quand deux requêtes, une valide et une invalide, produisent deux lignes exploitables.

### Axel Alacache — vérification extérieure

Script lancé hors du conteneur. Il envoie de vraies requêtes au conteneur, pas un `TestClient`. Il compare le modèle et le code observés aux valeurs attendues, et échoue en nommant la claim qui ne correspond pas. Prévoir une exécution volontairement cassée, et noter ce qu'elle laisse derrière elle.

Fini quand le script sort 0 sur le conteneur attendu et sort non nul quand le modèle ou le code ne correspond pas.

### Thomas Soubagne — README Deploy

Section `Deploy` du README. Elle répond aux dix questions du PDF (réglages, modèle, ready, panne, ligne de log, secrets, identité, valeur attendue, promesse de « deployed », panne provoquée). Relier dans `reports/` la section Lab 5 : commit, identifiant d'image, commande, requêtes et lignes de log.

Fini quand un lecteur du README sait démarrer le service et lancer la vérification sans demander à l'auteur.

## Lab 6 — CI, tests, Cloud Run

Prérequis : Lab 5 relu et mergé. PDF : `Week 3 — Lab 6`.
Puis tag annoté `m3`. Rapport personnel : `reports/week-3.md`.

| Partie | Owner | Relu par |
|---|---|---|
| Workflow | Axel Alacache | Victor Rouleau |
| Tests | Victor Rouleau | Nils Giraud |
| Image dans la CI | Thomas Soubagne | Axel Alacache |
| README CI et Cloud Run | Nils Giraud | Thomas Soubagne |

Thomas ouvre en plus une pull request avec un seul défaut crédible dans les tests de Victor. Il choisit le défaut lui-même et ne l'écrit pas ici. Victor ne doit pas le connaître à l'avance. Garder le log rouge, le correctif, puis le run vert sur cette même pull request.

### Axel Alacache — workflow

Partir de `.github/workflows/ci.yml`. Installation depuis le lock, permissions minimales, versions épinglées, délai limite. Dire dans le README quels changements lancent quels checks, dans quel ordre, et ce que la CI ne peut pas affirmer sur le modèle. Ne pas copier un run du laptop comme preuve de CI.

Fini quand une pull request vers `main` déclenche le workflow sur le commit poussé, et que le run est cité dans le rapport.

### Victor Rouleau — tests

Tests qui échouent pour les défauts qu'ils prétendent attraper. L'un d'eux recalcule un résultat déjà enregistré. Enregistrer le marqueur pytest dans `pyproject.toml` s'il y en a un. Montrer qu'un test peut devenir rouge, puis le réparer sans sauter le test ni baisser l'assertion.

Fini quand le rapport nomme le défaut, le test, le run rouge et le run vert.

### Thomas Soubagne — image dans la CI

Job qui construit l'image à partir du `Dockerfile`, sur le runner, sans le `.venv` du laptop. Le job doit pouvoir échouer si le build échoue. Ne pas muter un échec pour obtenir le vert.

Fini quand le log du runner montre le build de l'image pour le commit de la pull request.

### Nils Giraud — README CI et Cloud Run

Section `CI` du README : couverture, machine propre, déclencheur, ordre d'échec, ce que la CI prouve. Déploiement Cloud Run du service du Lab 5 seulement si `main` est vert. Connexion sans clé stockée. Dire comment on sait que la nouvelle révision est en ligne, et comment on rend le trafic à la révision précédente si le contrôle vivant échoue. Section Lab 6 dans le rapport d'équipe : run rouge, cause, commit de réparation, run vert, run de déploiement et contrôle de l'URL.

Fini quand le README permet de reproduire un échec en local, et que le déploiement cité est celui du workflow, pas celui d'un laptop.

## Lab 7 — pipeline, décision, modèle accepté

Prérequis : Lab 6 relu et mergé. PDF : `Lab 07`.
Entraînement 2011 seulement. Validation janvier–juin 2012. Pas de métrique sur juillet–décembre 2012. On ne change que les réglages du modèle, pas `data/raw/hour.csv`.

| Partie | Owner | Relu par |
|---|---|---|
| Politique | Thomas Soubagne | Axel Alacache |
| Commande du pipeline | Axel Alacache | Nils Giraud |
| Gate | Victor Rouleau | Thomas Soubagne |
| Promotion | Nils Giraud | Victor Rouleau |

### Thomas Soubagne — politique

Écrire la politique et la committer avant de produire un candidat. Elle dit quelle version acceptée sert de référence, sur quelles lignes on compare, ce que le score signifie, et quel écart compte. Section README `Pipeline and gate` : étape, point d'entrée, échec rejouable, sortie incomplète, identité du run.

Fini quand la politique est sur `main` avant le premier candidat évalué avec elle.

### Axel Alacache — commande du pipeline

Une commande documentée, depuis un checkout propre, produit un candidat à partir des entrées déclarées. Elle ne promeut pas le modèle. Ne pas écraser l'artefact accepté avant la décision du gate.

Fini quand un camarade peut lancer cette commande en suivant le README et obtenir un candidat identifié.

### Victor Rouleau — gate

La décision accepte ou rejette. Un rejet laisse l'état accepté inchangé. Une promotion garde la version acceptée qu'elle remplace. Enregistrer au moins un rejet réel. Ne pas forcer un succès s'il n'y a pas de candidat acceptable.

Fini quand le rapport montre un rejet qui n'a pas remplacé le modèle accepté, et une promotion qui a conservé la version précédente.

### Nils Giraud — promotion

Le service Cloud Run sert la version acceptée. La révision précédente reste disponible. Documenter comment récupérer le paquet accepté. Section Lab 7 du rapport d'équipe : politique, décisions, version servie.

Fini quand l'URL du service répond avec la version acceptée, et que la révision précédente existe encore.

## Lab 8 — incident et retour arrière

Prérequis : Lab 7 relu et mergé. PDF : `Lab 08`.
Garder `GET /health` et `POST /predict` avec le même contrat. `RUNBOOK.md` est à la racine du dépôt.

| Rôle | Owner |
|---|---|
| Opérateur | Nils Giraud |
| Injecteur | Victor Rouleau |
| Enregistreur | Axel Alacache |
| Runbook | Thomas Soubagne |

Victor choisit une seule panne réversible. Il ne la révèle pas à Nils avant que la chronologie du diagnostic soit écrite. Il ne l'écrit pas dans ce fichier.

### Thomas Soubagne — runbook

`RUNBOOK.md` : comment observer le service, quelles preuves regarder, comment revenir à la version acceptée précédente. Le README pointe vers ce runbook et vers le dossier de preuves.

Fini quand un opérateur peut suivre le runbook sans demander le scénario.

### Victor Rouleau — injecteur

Une panne réversible, dans le cadre convenu, après que le runbook est mergé. Ne pas casser le contrat de l'API de façon permanente. Prévenir l'enregistreur de l'heure, pas de la cause.

Fini quand la panne est visible sur le service et qu'elle peut être annulée.

### Nils Giraud — opérateur

Diagnostiquer à partir des logs, du runbook et des checks, sans qu'on lui donne la cause. Écrire ce qu'il a observé en premier, les hypothèses testées, et la conclusion.

Fini quand la chronologie permet à un autre membre de reconstruire la conclusion.

### Axel Alacache — enregistreur

Garder la chronologie et les preuves brutes dans `reports/`. Relier ces fichiers depuis le README et la section Lab 8 du rapport d'équipe. Trois captures au plus. Après le diagnostic, enregistrer le retour à l'état accepté et la vérification fraîche.

Fini quand le rapport relie le signal, l'explication et le comportement vérifié après le retour arrière.

## Ordre

1. Lab 5, quatre pull requests, puis merge.
2. Lab 6, quatre pull requests, plus la pull request de défaut de Thomas.
3. Tag annoté `m3` quand les Labs 5 et 6 sont relus.
4. Lab 7, quatre pull requests, puis merge.
5. Lab 8, runbook d'abord, panne ensuite.

Rapport personnel de chacun : `reports/week-3.md` pour les Labs 5 et 6, `reports/week-4.md` pour les Labs 7 et 8, dans son dépôt privé.
