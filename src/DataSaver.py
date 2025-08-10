from time import time
import pandas as pd
from src.utils import read_json
from pathlib import Path

class DataSaver:
    def __init__(self, parent):
        self.main_window = parent
        self.config = parent.config
        self.data = {}
        self.init_time = time()
        for param in ['time', 'N', 'P', 'M', 'T', 'f', 'L']:
            self.data[param] = []
        self.offsets = parent.offsets

    def add_to_matrix(self, input_dict, elapsed_time):
        """
        Добавляет значения из словаря в соответствующие матрицы.
        :param elapsed_time:
        :param input_dict: Словарь, где ключ — строка, значение — число.
        """
        self.data['time'].append(elapsed_time/1000)

        for key in ['f', 'T', 'N', 'P', 'L', 'M']:
            value = input_dict[key]
            if key in self.offsets:
                offset = self.offsets[key]
            else:
                offset = 0
            if key not in self.data:
                self.data[key] = []
            if value is not None:
                self.data[key].append(round(value-offset, 3))


    def get_matrices(self):
        """
        Возвращает все матрицы.
        :return: Словарь, где ключ — строка, значение — матрица (список списков).
        """
        return self.data

    def save_data(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        axis = read_json('axis.json')
        axis = {value: key for key, value in axis.items()}
        df = pd.DataFrame(self.data).rename(columns=axis)
        df.to_csv(path, index=False, sep='\t', decimal=',')


    def drop_data(self):
        for param in ['time', 'N', 'P', 'M', 'T', 'f', 'L']:
            self.data[param] = []
        self.main_window.time_offset = 0
