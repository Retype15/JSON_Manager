import os
import json

PROGRAM_NAME = 'JsonManager'

def get_config_folder():
    # Obtener la ruta de la carpeta de configuración
    if os.name == 'nt':  # Si es Windows
        config_folder = os.path.join(os.getenv('APPDATA'), PROGRAM_NAME)
    else:  # Si es macOS o Linux
        config_folder = os.path.join(os.path.expanduser('~'), '.config', PROGRAM_NAME)

    # Crear la carpeta si no existe
    os.makedirs(config_folder, exist_ok=True)

    return config_folder

def save_config(config, filename='config.json'):
    config_folder = get_config_folder()
    config_path = os.path.join(config_folder, filename)

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

def load_config(filename='config.json'):
    config_folder = get_config_folder()
    config_path = os.path.join(config_folder, filename)

    if not os.path.exists(config_path):
        return {}

    with open(config_path, 'r') as f:
        return json.load(f)
