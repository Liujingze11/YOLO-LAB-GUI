Install and run YOLO-BACKPROP
============================

Use Python 3.10 or newer. From the YOLO-LAB-GUI checkout::

    python -m pip install -e '.[yolo]'
    ./run-yolo-backprop.sh

The installed console command is ``yolo-backprop``. To choose a Python interpreter::

    YOLO_BACKPROP_PYTHON=/absolute/path/to/python ./run-yolo-backprop.sh

Linux desktop shortcut::

    python -m yolo_backprop.desktop

``run-isat.sh`` and ``ISAT_PYTHON`` remain legacy aliases. Existing ISAT annotation files and plugins are supported. This checkout must be installed from source; upstream ``isat-sam`` packages are a different application.
