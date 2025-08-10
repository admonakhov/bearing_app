import json
from PySide6.QtWidgets import QFileDialog
import time
from pathlib import Path

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


def moving_average(data, window_size=1):
    """
    Скользящее среднее для массива data с окном window_size.

    :param data: список или массив чисел
    :param window_size: размер окна (целое > 0)
    :return: список сглаженных значений
    """

    if len(data) < window_size:
        return data

    averages = []
    window_sum = sum(data[:window_size])
    averages.append(window_sum / window_size)

    for i in range(window_size, len(data)):
        window_sum += data[i] - data[i - window_size]
        averages.append(window_sum / window_size)

    return averages


def get_filepath(workdir, action=''):
    date_str = time.strftime("%d.%m.%Y")
    time_str = time.strftime("%H.%M.%S")
    if action:
        file_path = Path(f"{workdir}/{date_str}/{time_str}-{action}.csv")
    else:
        file_path = Path(f"{workdir}/{date_str}/{time_str}.csv")
    return file_path