import numpy as np
import pandas as pd
from pathlib import Path
from collections import deque
from PySide6.QtCore import QObject, QThread, Signal, Slot
from src.utils import read_json
import time
import shutil

CHUNK_SIZE = 10_000
MAX_POINTS_RAM = 100_000


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

def round_dataframe(df: pd.DataFrame, decimals: dict={'Время, с':2, 'Наработка, цикл':0, 'Уровень нагружения, кН':2,
                                                      'Крутящий момент, Нм':2, 'Температура, °С':2,
                                                      'Частота нагружения, Гц':2, 'Значение зазора, мм':3}) -> pd.DataFrame:
    """
    Округляет все числовые значения в DataFrame до указанного числа знаков.
    Строки и другие типы остаются без изменений.
    """
    for numeric_col in decimals.keys():

        df[numeric_col] = df[numeric_col].round(decimals[numeric_col])
    return df

class ChunkedLogger:
    """
    Пишет чанки по CHUNK_SIZE строк в отдельные файлы в папке сессии.
    При финализации сшивает все чанки + хвост в один файл.
    """
    def __init__(self, base_dir="results", axis_rename=None):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.axis_rename = axis_rename or {}
        self.session_dir = None
        self.rows_buffer = []
        self.chunks = []
        self.chunk_idx = 0
        self._start_new_session_dir()

    def _start_new_session_dir(self):
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.session_dir = self.base_dir / f"session-{stamp}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.rows_buffer.clear()
        self.chunks.clear()
        self.chunk_idx = 0

    def start_new_session(self):
        """Начать новую сессию (очистить список чанков, создать новую папку)."""
        self._start_new_session_dir()

    def _flush_chunk(self):
        if not self.rows_buffer:
            return
        self.chunk_idx += 1
        chunk_path = self.session_dir / f"chunk-{self.chunk_idx:05d}.tsv"

        chunk_path.parent.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(self.rows_buffer)
        if self.axis_rename:
            df = df.rename(columns=self.axis_rename)
        df = round_dataframe(df)
        df.to_csv(chunk_path, index=False, sep="\t", decimal=",")
        self.chunks.append(chunk_path)
        self.rows_buffer.clear()

    def append_rows(self, rows: list[dict]):
        """Добавить строки (внутренние имена колонок!), сбросить на диск при достижении CHUNK_SIZE."""
        if not rows:
            return
        self.rows_buffer.extend(rows)
        if len(self.rows_buffer) >= CHUNK_SIZE:
            self._flush_chunk()

    def finalize_to(self, out_path: Path, delete_chunks: bool = True) -> Path:
        """
        Дозаписать хвост в последний чанк (если есть), затем собрать все чанки в один файл out_path.
        После — опционально удалить временные файлы/папку сессии.
        """

        if self.rows_buffer:
            self._flush_chunk()

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.chunks:
            columns_internal = ['time', 'N', 'P', 'M', 'T', 'f', 'L']
            columns = [self.axis_rename.get(c, c) for c in columns_internal]
            pd.DataFrame(columns=columns).to_csv(out_path, index=False, sep="\t", decimal=",")
            return out_path

        with open(out_path, "wb") as fout:
            for i, chunk in enumerate(self.chunks):
                with open(chunk, "rb") as fin:
                    if i == 0:
                        shutil.copyfileobj(fin, fout)
                    else:
                        fin.readline()
                        shutil.copyfileobj(fin, fout)

        if delete_chunks:
            try:
                shutil.rmtree(self.session_dir)
            except Exception:
                pass
        self.rows_buffer.clear()
        self.chunks.clear()
        self.chunk_idx = 0
        return out_path


class DataSaverWorker(QObject):
    """Работает в отдельном потоке, принимает новые данные и хранит их (RAM окно + чанки)."""
    finished = Signal()

    def __init__(self, offsets, params=None, max_points_ram: int = MAX_POINTS_RAM):
        super().__init__()
        if params is None:
            params = ['time', 'N', 'P', 'M', 'T', 'f', 'L']

        self.offsets = offsets
        self.max_points_ram = int(max_points_ram)
        self.data = {p: deque(maxlen=self.max_points_ram) for p in params}
        self._running = True

        axis = read_json('axis.json')
        axis_rename = {v: k for k, v in axis.items()}

        self.logger = ChunkedLogger(base_dir="results", axis_rename=axis_rename)
        self._batch = []

    @Slot(dict, float)
    def add_data(self, input_dict, elapsed_time_ms: float):
        """
        Добавляет новую точку во внутренние очереди (RAM-окно) и в батч для чанк-записи.
        Кладём NaN для отсутствующих значений, чтобы все ряды всегда были одной длины.
        """
        if not self._running:
            return

        # время (сек)
        t = float(elapsed_time_ms) / 1000.0
        self.data['time'].append(t)

        row = {'time': t}

        for key in ['N','P', 'M', 'L', 'T', 'f']:
            val = input_dict.get(key, None)
            if val is None:
                v = np.nan
            else:
                off = self.offsets.get(key, 0.0)
                if key == 'N':
                    v = int(val - off)
                else:
                    v = float(val - off)
            self.data[key].append(v)
            row[key] = v

        self._batch.append(row)

        if len(self._batch) >= CHUNK_SIZE:
            try:
                self.logger.session_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            self.logger.append_rows(self._batch)
            self._batch.clear()

    def get_data(self):
        """Оперативное окно для графика (numpy-массивы)."""
        return {k: np.fromiter(v, dtype=np.float32) if len(v) else np.array([], dtype=np.float32)
                for k, v in self.data.items()}

    def clear(self):
        for k in self.data.keys():
            self.data[k].clear()

    def start_new_session(self):
        """Сбросить оперативное окно и начать новую папку сессии для чанков."""
        self.clear()
        self.logger.start_new_session()
        self._batch.clear()

    def finalize_to(self, out_path: Path):
        """Дозаписать хвост и сшить все чанки в единый файл."""
        if self._batch:
            self.logger.append_rows(self._batch)
            self._batch.clear()

        return self.logger.finalize_to(out_path)

    def stop(self):
        self._running = False
        self.finished.emit()


class DataSaver(QObject):
    """Фасад из GUI: поток + сигнал для добавления данных, API для начала/сшивки."""
    data_in = Signal(dict, float)

    def __init__(self, parent):
        super().__init__()
        self.main_window = parent
        self.config = parent.config
        self.offsets = parent.offsets
        self._filter_frame = int(self.config.get('filter_frame',
                                self.config.get('graph_filter_frame', 0)))
        channels_str = str(self.config.get('filter_channels',
                                self.config.get('graph_filter_channels', ''))).strip()
        self._filter_channels = [c.strip() for c in channels_str.split(',') if c.strip()]
        # банк фильтров по каналам
        self._filters = {ch: RollingMean(self._filter_frame) for ch in self._filter_channels}

        max_points_ram = int(self.config.get('datasaver_max_points', MAX_POINTS_RAM))

        self.thread = QThread()
        self.worker = DataSaverWorker(self.offsets, max_points_ram=max_points_ram)
        self.worker.moveToThread(self.thread)
        self.data_in.connect(self.worker.add_data)
        self.thread.start()

    def apply_filters(self, input_dict: dict) -> dict:
        """
        Вернёт копию input_dict с применённым скользящим средним
        для каналов из filter_channels. Не трогает None/NaN.
        """
        if not self._filter_channels or self._filter_frame <= 0:
            return dict(input_dict)
        out = dict(input_dict)
        for ch in self._filter_channels:
            if ch in out:
                v = out[ch]
                # пропуски данных: сбрасываем фильтр, значение оставляем как есть
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    if ch in self._filters:
                        self._filters[ch].reset()
                else:
                    # float -> фильтр -> округление до 3 знаков для консистентности
                    filt = self._filters[ch]
                    out[ch] = float(np.round(filt.update(float(v)), 3))
        return out

    def add_to_matrix(self, input_dict, elapsed_time_ms):
        self.data_in.emit(input_dict, elapsed_time_ms)

    def get_matrices(self):
        return self.worker.get_data()

    # --- новые методы ---
    def start_session(self):
        """Начать новую сессию записи (новая папка, чистое оперативное окно)."""
        self.worker.start_new_session()
        self.main_window.time_offset = 0
        for f in self._filters.values():
            f.reset()

    def save_data(self, path):
        """
        Сшивает все чанки текущей сессии + хвост в единый файл `path`.
        Это вызывается при стопе/выгрузке.
        """
        path = Path(path)
        result = self.worker.finalize_to(path)
        return result

    def drop_data(self):
        """Сбросить только оперативное окно (график), без изменения чанков."""
        self.worker.clear()
        self.main_window.time_offset = 0
        for f in self._filters.values():
            f.reset()

    def close(self):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()