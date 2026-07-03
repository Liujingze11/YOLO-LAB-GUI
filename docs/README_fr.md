# YOLO Lab GUI

[English](README.md) | [中文](README_zh.md) | [Español](README_es.md)

Outil de formation/inférence de segmentation YOLO avec interface minimaliste style Apple.

## Fonctionnalités

- **Entraînement** — Modes Nouveau/Reprendre/Ajuster, augmentation de données, gestion des préréglages
- **Inférence** — Segmentation d'image avec suivi de progression
- **Outils** — Division de jeux de données, création d'étiquettes vides
- **Journaux & Résultats** — Consultation des journaux d'entraînement et exploration des expériences
- Téléchargement automatique des poids initiaux depuis le menu déroulant
- Mode clair/sombre
- Support 4 langues (zh/en/fr/es) pour l'interface et la sortie terminal
- Exécution en sous-processus avec possibilité d'arrêt

## Démarrage Rapide

```bash
git clone https://github.com/Liujingze11/YOLO-LAB-GUI.git
cd YOLO-LAB-GUI
bash setup.sh
conda activate yolo
python gui/main.py
```

## Prérequis

- Python 3.10+
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- ultralytics >= 8.0.0, PySide6 >= 6.5.0, PyYAML >= 6

Installation manuelle :

```bash
conda create -n yolo python=3.10 -y
conda activate yolo
pip install -r requirements.txt
```

## Utilisation

### Entraînement

1. Passez à l'onglet Entraînement
2. Configurez `data.yaml`, les hyperparamètres et le mode
3. Cliquez sur Démarrer

Trois modes :
- **Nouveau** — Depuis les poids initiaux
- **Reprendre** — Continuer depuis last.pt
- **Ajuster** — Basé sur le best.pt d'une expérience historique

### Inférence

1. Passez à l'onglet Inférence
2. Sélectionnez le modèle, la source et le répertoire de sortie
3. Cliquez sur Démarrer

### Langue

Utilisez le menu déroulant en haut à droite pour basculer entre Chinois / English / Français / Español.

## Résultats

- Résultats d'entraînement : `outputs/results/<experiment_name>/weights/`
- Résultats d'inférence : `outputs/predict/`
- Journaux CSV : `outputs/logs/`

## License

MIT
