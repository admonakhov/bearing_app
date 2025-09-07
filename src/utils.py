import json
from PySide6.QtWidgets import QFileDialog
import time
from pathlib import Path
import numpy as np
from collections import deque


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


def read_json(path):
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


def get_filepath(workdir, action=''):
    date_str = time.strftime("%d.%m.%Y")
    time_str = time.strftime("%H.%M.%S")
    if action:
        file_path = Path(f"{workdir}/{date_str}/{time_str}-{action}.csv")
    else:
        file_path = Path(f"{workdir}/{date_str}/{time_str}.csv")
    return file_path


class RollingMean:
    """O(1) скользящее среднее по фиксированному окну."""
    def __init__(self, window: int):
        self.window = max(int(window), 0)
        self.buf = deque(maxlen=self.window if self.window > 0 else 1)
        self.sum = 0.0

    def reset(self):
        self.buf.clear()
        self.sum = 0.0

    def update(self, x: float) -> float:
        if self.window <= 0:
            return x
        if len(self.buf) == self.buf.maxlen:
            self.sum -= self.buf[0]
        self.buf.append(x)
        self.sum += x
        return self.sum / len(self.buf)