from pathlib import Path

from PySide6.QtCore import QThread, Signal


class DurationWorker(QThread):
    duration_signal = Signal(str, float)
    error_signal = Signal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            from mediaseg_core import get_duration

            duration = get_duration(Path(self.file_path))
            self.duration_signal.emit(self.file_path, duration)
        except Exception:
            self.error_signal.emit(self.file_path)


class Worker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, input_file, max_size_mb, output_dir=None):
        super().__init__()
        self.input_file = input_file
        self.max_size_mb = max_size_mb
        self.output_dir = output_dir

    def run(self):
        try:
            from mediaseg_core import split_media

            input_file_path = Path(self.input_file).resolve()
            outdir_path = split_media(
                input_file=str(input_file_path),
                max_size_mb=self.max_size_mb,
                logger=self.log_signal.emit,
                output_dir=self.output_dir,
            )
            self.finished_signal.emit(str(outdir_path))
        except Exception as exc:
            self.error_signal.emit(str(exc))
