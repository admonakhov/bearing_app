import json
from PySide6.QtWidgets import QFileDialog


def read_conf(path, dtype=str):
    config = {}
    with open(path, 'r') as _cfg:
        lines = _cfg.read().split('\n')
    for line in lines:
        if len(line) > 1:
            name, atr = line.split(' ')
            atr = dtype(atr)
            config[name] = atr
    return config

def write_conf(path, config:dict):
    with open(path, 'w') as _cfg:
        for key in config.keys():
            _cfg.write(f'{key} {config[key]}\n')


def read_json(path, dtype=str):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data

def get_file_path():
    file_path, _ = QFileDialog.getSaveFileName(
        None,
        "Создать новый файл",
        "",
        "Текстовые файлы (*.csv);;Все файлы (*.*)"
    )

    return file_path