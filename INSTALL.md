# Guide d'Installation L.I.G.M.A.

Ce guide vous accompagnera dans l'installation complète de L.I.G.M.A. sur votre machine locale.

---

## 1. Installation d'Ollama

L.I.G.M.A. utilise **Ollama** pour l'inférence locale des modèles.

1. **Téléchargement** : Rendez-vous sur [ollama.com](https://ollama.com) et téléchargez la version correspondant à votre système (Windows, macOS ou Linux).
2. **Installation** : Suivez les instructions de l'installeur.
3. **Téléchargement des modèles** : Vous devez installer au moins un modèle pour faire tourner le bot. Ouvrez un terminal et exécutez l'une des commandes suivantes :

   - **Modèle recommandé (équilibré)** :
     ```bash
     ollama pull llama3.2:3b
     ```
   - **Modèle léger (rapide)** :
     ```bash
     ollama pull llama3.2:1b
     ```
   - **Modèle avancé (nécessite plus de RAM/VRAM)** :
     ```bash
     ollama pull qwen2.5-coder:7b
     ```

---

## 2. Installation de `uv`

`uv` est un gestionnaire de paquets Python extrêmement rapide que nous utilisons pour ce projet.

- **Windows (PowerShell)** :
  ```powershell
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **macOS / Linux** :
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

---

## 3. Installation du Projet

Une fois Ollama et `uv` installés, suivez ces étapes :

1. **Cloner le projet** :
   ```bash
   git clone https://github.com/haksolot/ligma.git
   cd ligma
   ```

2. **Installer les dépendances** :
   `uv` va automatiquement créer un environnement virtuel et installer tout le nécessaire (y compris Python 3.13 s'il n'est pas présent).
   ```bash
   uv sync
   ```

3. **Configurer les variables d'environnement** :
   Copiez le fichier d'exemple et remplissez-le avec vos clés.
   ```bash
   cp .env.example .env
   ```
   *Éditez le fichier `.env` pour y ajouter votre `DISCORD_TOKEN`.*

---

## 4. Lancement

Pour démarrer L.I.G.M.A. :

```bash
uv run run.py
```

---

## Résumé des commandes utiles

| Action | Commande |
| --- | --- |
| Lancer le bot | `uv run run.py` |
| Mettre à jour les dépendances | `uv sync` |
| Ajouter un nouveau modèle | `ollama pull <nom_du_modele>` |
| Lister les modèles installés | `ollama list` |

---

## Optionnel : Utiliser OpenRouter au lieu d'Ollama

L.I.G.M.A. peut utiliser **OpenRouter** pour l'inférence cloud au lieu d'Ollama local.

### Pourquoi OpenRouter ?
- Accès à des modèles puissants (GPT-4, Claude, Gemini...)
- Pas besoin de GPU local
- Fonctionne même si Ollama n'est pas installé

### Configuration

1. **Obtenez une clé API** sur [openrouter.ai/keys](https://openrouter.ai/keys)

2. **Modifiez votre `.env`** :
   ```env
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=sk-or-v1-...
   DEFAULT_MODEL=openai/gpt-4o
   ```

3. **Lancez le bot** — pas besoin d'Ollama ni de modèle local.

### Modèles recommandés

| Modèle | Description |
| --- | --- |
| `openai/gpt-4o` | GPT-4 Omni — excellent équilibre性能 |
| `anthropic/claude-3.5-sonnet` | Claude — très bonne raison |
| `google/gemini-2.0-flash` | Gemini — rapide et gratuit |

Tous les modèles disponibles sur [openrouter.ai/models](https://openrouter.ai/models).

### Changer de provider à la volée

En runtime (commandes slash, creator only) :
- `/provider status` — voir le provider actuel
- `/provider ollama` — repasser sur Ollama local
- `/provider openrouter` — repasser sur OpenRouter
