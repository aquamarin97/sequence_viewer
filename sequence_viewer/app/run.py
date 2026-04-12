import sys

from PyQt5.QtWidgets import QApplication

from sequence_viewer.app.main_window import MainWindow
from sequence_viewer.workspace.workspace import SequenceWorkspaceWidget


def run():
    app = QApplication(sys.argv)

    from sequence_viewer.settings.font_families import load_embedded_fonts

    load_embedded_fonts()

    workspace = SequenceWorkspaceWidget()
    workspace.resize(1200, 600)
    window = MainWindow(workspace)
    window.resize(1200, 650)
    window.show()
    return app.exec_()


