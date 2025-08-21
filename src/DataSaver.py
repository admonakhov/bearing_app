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

        for key in ['f', 'T', 'N', 'P', 'L', 'M']:
            val = input_dict.get(key, None)
            if val is None:
                v = np.nan
            else:
                off = self.offsets.get(key, 0.0)
                if key == 'N':
                    v = int(val - off)
                else:
                    v = float(np.round(val - off, 3))
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

        max_points_ram = int(self.config.get('datasaver_max_points', MAX_POINTS_RAM))

        self.thread = QThread()
        self.worker = DataSaverWorker(self.offsets, max_points_ram=max_points_ram)
        self.worker.moveToThread(self.thread)
        self.data_in.connect(self.worker.add_data)
        self.thread.start()

    def add_to_matrix(self, input_dict, elapsed_time_ms):
        self.data_in.emit(input_dict, elapsed_time_ms)

    def get_matrices(self):
        return self.worker.get_data()

    # --- новые методы ---
    def start_session(self):
        """Начать новую сессию записи (новая папка, чистое оперативное окно)."""
        self.worker.start_new_session()
        self.main_window.time_offset = 0

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

    def close(self):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()