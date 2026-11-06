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
Tu réalises uniquement son étape dans ce lab. Tu ne codes pas les étapes des
autres. Tu ouvres une seule pull request, sur une branche à toi.

Dans un lab, une seule pull request à la fois. Tu ne commences pas tant que
l'étape précédente n'est pas mergée sur `main`. La personne qui fait l'étape
suivante relit, demande le correctif s'il faut, puis merge. Ensuite seulement
elle ouvre sa pull request.

Avant de coder, lis le PDF du lab dans `slides/week03` ou `slides/week04` du
dépôt du cours. Les choix de conception vont dans le README : le choix retenu,
l'option écartée, et pourquoi.

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
Victor mène. Chaîne : Victor, puis Nils, puis Thomas, puis Axel.

| Étape | Owner | Relu et mergé par | Démarre quand |
|---|---|---|---|
| 1. Démarrage | Victor Rouleau | Nils Giraud | tout de suite |
| 2. Logs | Nils Giraud | Thomas Soubagne | étape 1 mergée |
| 3. Vérification extérieure | Thomas Soubagne | Axel Alacache | étape 2 mergée |
| 4. README Deploy | Axel Alacache | Victor Rouleau | étape 3 mergée |

### 1. Victor Rouleau — démarrage

Étendre le `Dockerfile` du Lab 4 pour que le service démarre avec des réglages passés au `docker run` (`-e`, port publié seulement sur `127.0.0.1`). Écrire dans le README ce que « deployed » veut dire et qui lance la vérification finale. Répondre aux questions : quels réglages changent entre le laptop et le conteneur, d'où vient le modèle au démarrage, quand le service est « ready », que dit-il si le modèle manque.

Fini quand un camarade peut démarrer le conteneur en suivant seulement le README, et que `/health` et `/predict` répondent comme au Lab 4. Le service doit exposer l'identité du modèle et du code, pour l'étape 3.

### 2. Nils Giraud — logs

Une ligne de log par requête, lisible avec `docker logs` sans revoir la requête. On doit pouvoir y distinguer une requête acceptée et une requête rejetée, le statut, la durée, et l'identité du modèle. Décider et documenter ce qui ne doit jamais apparaître dans un log. Ne pas retirer les champs déjà renvoyés par l'API.

Fini quand deux requêtes, une valide et une invalide, produisent deux lignes exploitables.

### 3. Thomas Soubagne — vérification extérieure

Script lancé hors du conteneur. Il envoie de vraies requêtes au conteneur, pas un `TestClient`. Il compare le modèle et le code observés aux valeurs attendues, et échoue en nommant la claim qui ne correspond pas. Prévoir une exécution volontairement cassée, et noter ce qu'elle laisse derrière elle.

Fini quand le script sort 0 sur le conteneur attendu et sort non nul quand le modèle ou le code ne correspond pas.

### 4. Axel Alacache — README Deploy

Section `Deploy` du README. Elle répond aux dix questions du PDF avec les commandes déjà mergées aux étapes 1 à 3. Relier dans `reports/` la section Lab 5 : commit, identifiant d'image, commande, requêtes et lignes de log.

Fini quand un lecteur du README sait démarrer le service et lancer la vérification sans demander à l'auteur.

## Lab 6 — CI, tests, Cloud Run

Prérequis : Lab 5 mergé. PDF : `Week 3 — Lab 6`.
Nils mène. Chaîne : Nils, puis Thomas, puis Axel, puis Victor.
Après les quatre merges, tag annoté `m3`. Rapport personnel : `reports/week-3.md`.

| Étape | Owner | Relu et mergé par | Démarre quand |
|---|---|---|---|
| 1. Workflow | Nils Giraud | Thomas Soubagne | Lab 5 mergé |
| 2. Tests | Thomas Soubagne | Axel Alacache | étape 1 mergée |
| 3. Image dans la CI | Axel Alacache | Victor Rouleau | étape 2 mergée, et la PR de défaut réparée |
| 4. README CI et Cloud Run | Victor Rouleau | Nils Giraud | étape 3 mergée |

Après le merge de l'étape 2, Axel ouvre une pull request avec un seul défaut crédible dans les tests de Thomas. Il choisit le défaut lui-même et ne l'écrit pas ici. Thomas ne le connaît pas à l'avance. Thomas le répare sur cette pull request : log rouge, correctif, run vert. Ensuite Axel commence l'étape 3.

### 1. Nils Giraud — workflow

Partir de `.github/workflows/ci.yml`. Installation depuis le lock, permissions minimales, versions épinglées, délai limite. Dire dans le README quels changements lancent quels checks, dans quel ordre, et ce que la CI ne peut pas affirmer sur le modèle. Ne pas copier un run du laptop comme preuve de CI.

Fini quand une pull request vers `main` déclenche le workflow sur le commit poussé.

### 2. Thomas Soubagne — tests

Tests qui échouent pour les défauts qu'ils prétendent attraper. L'un d'eux recalcule un résultat déjà enregistré. Enregistrer le marqueur pytest dans `pyproject.toml` s'il y en a un. Montrer qu'un test peut devenir rouge sur la CI de l'étape 1, puis le réparer sans sauter le test ni baisser l'assertion.

Fini quand le rapport nomme le défaut, le test, le run rouge et le run vert.

### 3. Axel Alacache — image dans la CI

Job qui construit l'image à partir du `Dockerfile`, sur le runner, sans le `.venv` du laptop. Le mettre dans un fichier de workflow à part, pas dans le fichier déjà mergé à l'étape 1. Le job doit pouvoir échouer si le build échoue. Ne pas muter un échec pour obtenir le vert.

Fini quand le log du runner montre le build de l'image pour le commit de la pull request.

### 4. Victor Rouleau — README CI et Cloud Run

Section `CI` du README : couverture, machine propre, déclencheur, ordre d'échec, ce que la CI prouve. Déploiement Cloud Run du service du Lab 5 seulement si `main` est vert. Connexion sans clé stockée. Dire comment on sait que la nouvelle révision est en ligne, et comment on rend le trafic à la révision précédente si le contrôle vivant échoue. Section Lab 6 dans le rapport d'équipe : run rouge, cause, commit de réparation, run vert, run de déploiement et contrôle de l'URL.

Fini quand le README permet de reproduire un échec en local, et que le déploiement cité est celui du workflow, pas celui d'un laptop.

## Lab 7 — pipeline, décision, modèle accepté

Prérequis : Lab 6 mergé. PDF : `Lab 07`.
Thomas mène. Chaîne : Thomas, puis Axel, puis Victor, puis Nils.
Entraînement 2011 seulement. Validation janvier–juin 2012. Pas de métrique sur juillet–décembre 2012. On ne change que les réglages du modèle, pas `data/raw/hour.csv`.

| Étape | Owner | Relu et mergé par | Démarre quand |
|---|---|---|---|
| 1. Politique | Thomas Soubagne | Axel Alacache | Lab 6 mergé |
| 2. Commande du pipeline | Axel Alacache | Victor Rouleau | étape 1 mergée |
| 3. Gate | Victor Rouleau | Nils Giraud | étape 2 mergée |
| 4. Promotion | Nils Giraud | Thomas Soubagne | étape 3 mergée |

### 1. Thomas Soubagne — politique

Écrire la politique et la committer avant tout candidat. Elle dit quelle version acceptée sert de référence, sur quelles lignes on compare, ce que le score signifie, et quel écart compte. Section README `Pipeline and gate` : étape, point d'entrée, échec rejouable, sortie incomplète, identité du run.

Fini quand la politique est sur `main`.

### 2. Axel Alacache — commande du pipeline

Une commande documentée, depuis un checkout propre, produit un candidat à partir des entrées déclarées et de la politique déjà mergée. Elle ne promeut pas le modèle. Ne pas écraser l'artefact accepté.

Fini quand un camarade peut lancer cette commande en suivant le README et obtenir un candidat identifié.

### 3. Victor Rouleau — gate

La décision accepte ou rejette selon la politique mergée. Un rejet laisse l'état accepté inchangé. Une promotion garde la version acceptée qu'elle remplace. Enregistrer au moins un rejet réel, à partir d'un candidat de l'étape 2. Ne pas forcer un succès s'il n'y a pas de candidat acceptable.

Fini quand le rapport montre un rejet qui n'a pas remplacé le modèle accepté, et une promotion qui a conservé la version précédente.

### 4. Nils Giraud — promotion

Le service Cloud Run sert la version acceptée par le gate. La révision précédente reste disponible. Documenter comment récupérer le paquet accepté. Section Lab 7 du rapport d'équipe : politique, décisions, version servie.

Fini quand l'URL du service répond avec la version acceptée, et que la révision précédente existe encore.

## Lab 8 — incident et retour arrière

Prérequis : Lab 7 mergé. PDF : `Lab 08`.
Axel mène le runbook. Chaîne : Axel, puis Victor, puis Nils, puis Thomas.
Garder `GET /health` et `POST /predict` avec le même contrat. `RUNBOOK.md` est à la racine du dépôt.

| Étape | Owner | Relu et mergé par | Démarre quand |
|---|---|---|---|
| 1. Runbook | Axel Alacache | Victor Rouleau | Lab 7 mergé |
| 2. Panne | Victor Rouleau | Thomas Soubagne | étape 1 mergée |
| 3. Diagnostic | Nils Giraud | Axel Alacache | la panne est en place |
| 4. Chronologie | Thomas Soubagne | Victor Rouleau | étape 3 mergée |

Nils ne lit pas la pull request de l'étape 2. Thomas la relit à sa place. Victor ne lui dit pas la cause avant que le diagnostic soit écrit.

### 1. Axel Alacache — runbook

`RUNBOOK.md` : comment observer le service, quelles preuves regarder, comment revenir à la version acceptée précédente. Le README pointe vers ce runbook.

Fini quand un opérateur peut suivre le runbook sans connaître la panne à l'avance.

### 2. Victor Rouleau — injecteur

Une panne réversible, après le merge du runbook. Ne pas casser le contrat de l'API de façon permanente. Prévenir Thomas de l'heure, pas Nils. Ne pas écrire la cause dans ce fichier ni dans un message à Nils.

Fini quand la panne est visible sur le service et qu'elle peut être annulée.

### 3. Nils Giraud — opérateur

Diagnostiquer à partir des logs, du runbook et des checks, sans lire la pull request de Victor. Écrire ce qu'il a observé en premier, les hypothèses testées, et la conclusion.

Fini quand la chronologie permet à un autre membre de reconstruire la conclusion.

### 4. Thomas Soubagne — enregistreur

Garder la chronologie et les preuves brutes dans `reports/`. Relier ces fichiers depuis le README et la section Lab 8 du rapport d'équipe. Trois captures au plus. Enregistrer le retour à l'état accepté et la vérification fraîche.

Fini quand le rapport relie le signal, l'explication et le comportement vérifié après le retour arrière.

## Ordre des labs

1. Lab 5, étapes 1 à 4, chacune mergée avant la suivante.
2. Lab 6, étapes 1 à 4, plus la pull request de défaut d'Axel entre les étapes 2 et 3.
3. Tag annoté `m3`.
4. Lab 7, étapes 1 à 4.
5. Lab 8, étapes 1 à 4.

Rapport personnel de chacun : `reports/week-3.md` pour les Labs 5 et 6, `reports/week-4.md` pour les Labs 7 et 8, dans son dépôt privé.
