# sequence_viewer/app/main_window.py
from pathlib import Path

from PyQt5.QtWidgets import QAction, QFileDialog, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self, workspace):
        super().__init__()
        self.workspace = workspace
        self._theme_dev_dialog = None
        self._nucleotide_dev_dialog = None
        self._annotation_dev_dialog = None
        # SQXReaders must stay open while their LazySequences are live.
        self._sqx_readers: list = []
        self._workers: list = []
        self.setWindowTitle("MSA Viewer")
        self.setCentralWidget(workspace)
        self._build_menu()

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        open_action = QAction("Open FASTA...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._import_fasta_dialog)
        file_menu.addAction(open_action)

        open_aligned_action = QAction("Open Aligned FASTA...", self)
        open_aligned_action.setShortcut("Ctrl+Shift+O")
        open_aligned_action.triggered.connect(self._import_aligned_fasta_dialog)
        file_menu.addAction(open_aligned_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        annotate_menu = menubar.addMenu("Annotate")
        find_motifs_action = QAction("Find Motifs...", self)
        find_motifs_action.setShortcut("Ctrl+F")
        find_motifs_action.triggered.connect(self.workspace.open_find_motifs_dialog)
        annotate_menu.addAction(find_motifs_action)
        annotate_menu.addSeparator()
        clear_ann_action = QAction("Clear All Annotations", self)
        clear_ann_action.triggered.connect(self.workspace.clear_annotations)
        annotate_menu.addAction(clear_ann_action)

        view_menu = menubar.addMenu("View")
        toggle_dark_action = QAction("Toggle Dark Mode", self)
        toggle_dark_action.setShortcut("Ctrl+D")
        toggle_dark_action.triggered.connect(self._toggle_dark_mode)
        view_menu.addAction(toggle_dark_action)

        settings_menu = menubar.addMenu("Settings")
        display_settings_action = QAction("Display Settings...", self)
        display_settings_action.triggered.connect(self._open_display_settings)
        settings_menu.addAction(display_settings_action)

        development_menu = menubar.addMenu("Development")
        theme_dev_action = QAction("Theme Colors", self)
        theme_dev_action.triggered.connect(self._open_theme_development_tool)
        development_menu.addAction(theme_dev_action)
        nucleotide_dev_action = QAction("Nucleotide Colors", self)
        nucleotide_dev_action.triggered.connect(self._open_nucleotide_development_tool)
        development_menu.addAction(nucleotide_dev_action)
        annotation_dev_action = QAction("Annotation Colors", self)
        annotation_dev_action.triggered.connect(self._open_annotation_development_tool)
        development_menu.addAction(annotation_dev_action)

    def _import_fasta_dialog(self):
        file_filter = "FASTA Files (*.fasta *.fa *.fna *.faa *.ffn *.frn *.aln);;All Files (*)"
        file_paths, _ = QFileDialog.getOpenFileNames(self, "FASTA Dosyasi Sec", "", file_filter)
        for path in file_paths:
            self._load_fasta_as_sqx(path, aligned=False)

    def _import_aligned_fasta_dialog(self):
        file_filter = "FASTA Files (*.fasta *.fa *.fna *.faa *.ffn *.frn *.aln);;All Files (*)"
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Aligned FASTA Dosyasi Sec", "", file_filter)
        for path in file_paths:
            self._load_fasta_as_sqx(path, aligned=True)
    def _load_fasta_as_sqx(self, path_str: str, aligned: bool = False) -> None:
        import time
        fasta_path = Path(path_str)
        sqx_path = fasta_path.with_suffix('.sqx')

        if sqx_path.exists():
            t0 = time.perf_counter()
            self._start_load_worker(sqx_path, aligned)
            # Load worker async, zamanlamayı on_reader_loaded'da alacağız
            self._t0 = t0
            return

        t0 = time.perf_counter()
        self._t0 = t0

        from sequence_viewer.app.sqx_conversion_worker import SQXConversionWorker
        worker = SQXConversionWorker(fasta_path, sqx_path)
        worker.finished.connect(lambda p: (
            print(f"[TIMING] Dönüşüm: {time.perf_counter() - self._t0:.2f}s"),
            self.__dict__.update({'_t1': time.perf_counter()}),
            self._start_load_worker(Path(p), aligned)
        ))
        worker.failed.connect(lambda msg: print(f"SQX donusum hatasi: {msg}"))
        self._register_worker(worker)
        worker.start()

    def _start_load_worker(self, sqx_path: Path, aligned: bool) -> None:
        """Open .sqx directory in background; records load lazily on first access."""
        from sequence_viewer.app.sqx_conversion_worker import SQXLoadWorker
        worker = SQXLoadWorker(sqx_path)
        worker.reader_ready.connect(
            lambda reader: self._on_reader_loaded(reader, aligned)
        )
        worker.failed.connect(lambda msg: print(f"SQX yukleme hatasi: {msg}"))
        self._register_worker(worker)
        worker.start()

    def _on_reader_loaded(self, reader, aligned: bool) -> None:
        import time
        if hasattr(self, '_t1'):
            print(f"[TIMING] SQX okuma: {time.perf_counter() - self._t1:.2f}s")
        if hasattr(self, '_t0'):
            print(f"[TIMING] Toplam: {time.perf_counter() - self._t0:.2f}s")
        self._sqx_readers.append(reader)
        alignment_metadata = None
        if aligned and reader.sequence_count() > 0:
            from sequence_viewer.model.alignment_metadata import AlignmentMetadata
            alignment_metadata = AlignmentMetadata(
                algorithm="imported", source="aligned FASTA file"
            )
        self.workspace.attach_reader(reader, alignment_metadata=alignment_metadata)

    def _register_worker(self, worker) -> None:
        self._workers.append(worker)
        worker.finished.connect(
            lambda: self._workers.remove(worker) if worker in self._workers else None
        )

    def closeEvent(self, event):
        for worker in self._workers:
            worker.quit()
            worker.wait()
        self._workers.clear()
        for reader in self._sqx_readers:
            reader.close()
        self._sqx_readers.clear()
        super().closeEvent(event)

    def _toggle_dark_mode(self):
        from settings.sequence_viewer.theme import theme_manager

        theme_manager.toggle()

    def _open_display_settings(self):
        from sequence_viewer.dialogs.display_settings_dialog import DisplaySettingsDialog

        dlg = DisplaySettingsDialog(self)
        dlg.exec_()

    def _open_theme_development_tool(self):
        from sequence_viewer.development.theme_devtool import ThemeDevelopmentDialog

        if self._theme_dev_dialog is None:
            self._theme_dev_dialog = ThemeDevelopmentDialog(self)
            self._theme_dev_dialog.finished.connect(
                lambda _: setattr(self, "_theme_dev_dialog", None)
            )
        self._theme_dev_dialog.show()
        self._theme_dev_dialog.raise_()
        self._theme_dev_dialog.activateWindow()

    def _open_nucleotide_development_tool(self):
        from sequence_viewer.development.nucleotide_devtool import NucleotideDevToolDialog

        if self._nucleotide_dev_dialog is None:
            self._nucleotide_dev_dialog = NucleotideDevToolDialog(self)
            self._nucleotide_dev_dialog.finished.connect(
                lambda _: setattr(self, "_nucleotide_dev_dialog", None)
            )
        self._nucleotide_dev_dialog.show()
        self._nucleotide_dev_dialog.raise_()
        self._nucleotide_dev_dialog.activateWindow()

    def _open_annotation_development_tool(self):
        from sequence_viewer.development.annotation_devtool import AnnotationDevToolDialog

        if self._annotation_dev_dialog is None:
            self._annotation_dev_dialog = AnnotationDevToolDialog(self)
            self._annotation_dev_dialog.finished.connect(
                lambda _: setattr(self, "_annotation_dev_dialog", None)
            )
        self._annotation_dev_dialog.show()
        self._annotation_dev_dialog.raise_()
        self._annotation_dev_dialog.activateWindow()

