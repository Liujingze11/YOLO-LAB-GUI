# YOLO Lab GUI

[English](README.md) | [中文](README_zh.md) | [Français](README_fr.md)

Herramienta de entrenamiento/inferencia de segmentación YOLO con interfaz minimalista estilo Apple.

## Funcionalidades

- **Entrenamiento** — Modos Nuevo/Reanudar/Ajustar, aumento de datos, gestión de preajustes
- **Inferencia** — Segmentación de imágenes con seguimiento de progreso
- **Herramientas** — División de conjuntos de datos, creación de etiquetas vacías
- **Registros y Resultados** — Consulta de registros de entrenamiento y exploración de experimentos
- Descarga automática de pesos iniciales desde el menú desplegable
- Modo claro/oscuro
- Soporte para 4 idiomas (zh/en/fr/es) en la interfaz y salida de terminal
- Ejecución en subproceso con capacidad de detención

## Inicio Rápido

```bash
git clone https://github.com/Liujingze11/YOLO-LAB-GUI.git
cd YOLO-LAB-GUI
bash setup.sh
conda activate yolo
python gui/main.py
```

## Requisitos

- Python 3.10+
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- ultralytics >= 8.0.0, PySide6 >= 6.5.0, PyYAML >= 6

Instalación manual:

```bash
conda create -n yolo python=3.10 -y
conda activate yolo
pip install -r requirements.txt
```

## Uso

### Entrenamiento

1. Cambie a la pestaña Entrenamiento
2. Configure `data.yaml`, hiperparámetros y modo
3. Haga clic en Iniciar

Tres modos:
- **Nuevo** — Desde pesos iniciales
- **Reanudar** — Continuar desde last.pt
- **Ajustar** — Basado en el best.pt de un experimento histórico

### Inferencia

1. Cambie a la pestaña Inferencia
2. Seleccione modelo, origen y directorio de salida
3. Haga clic en Iniciar

### Idioma

Use el menú desplegable en la esquina superior derecha para cambiar entre Chinese / English / Français / Español.

## Resultados

- Resultados de entrenamiento: `outputs/results/<experiment_name>/weights/`
- Resultados de inferencia: `outputs/predict/`
- Registros CSV: `outputs/logs/`

## Licencia

MIT
