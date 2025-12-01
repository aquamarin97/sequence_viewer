# msa_viewer/widgets/workspace.py

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QScrollBar,
)

from features.sequence_viewer.sequence_viewer_widget import SequenceViewerWidget
from features.navigation_ruler.navigation_ruler_widget import RulerWidget
from features.position_ruler.position_ruler_widget import SequencePositionRulerWidget
from features.header_viewer.header_viewer_widget import HeaderViewerWidget
from features.header_viewer.header_spacer_widgets import HeaderPositionSpacerWidget, HeaderTopWidget



class SequenceWorkspaceWidget(QWidget):
    """
    Solda: HeaderTopWidget + (boş spacer) + HeaderViewer
    Sağda: Navigation Ruler + SequencePositionRuler + SequenceViewer
    Satırlar dikeyde piksel piksel hizalı.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        char_width: float = 12.0,
        char_height: float = 18.0,
    ) -> None:
        super().__init__(parent)

        row_height = int(round(char_height))
        ruler_height = 28  # Navigation Ruler yüksekliği
        pos_ruler_height = 24  # Position Ruler yüksekliği

        # --- Sol panel: HeaderTop + spacer + HeaderViewer ---
        self.header_viewer = HeaderViewerWidget(
            parent=self,
            row_height=row_height,
            initial_width=160.0,
        )
        self.header_pos_spacer = HeaderPositionSpacerWidget(
            height=pos_ruler_height,
            parent=self,
        )
        self.header_top = HeaderTopWidget(height=ruler_height, parent=self)

        self.left_panel = QWidget(self)  # 🔹 referansı sakla
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(self.header_top)
        left_layout.addWidget(self.header_pos_spacer)
        left_layout.addWidget(self.header_viewer)

        # --- Sağ panel: Navigation Ruler + Position Ruler + SequenceViewer ---
        self.sequence_viewer = SequenceViewerWidget(
            parent=self,
            char_width=char_width,
            char_height=row_height,
        )

        self.ruler = RulerWidget(self.sequence_viewer, parent=self)
        self.pos_ruler = SequencePositionRulerWidget(self.sequence_viewer, parent=self)

        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.ruler)
        right_layout.addWidget(self.pos_ruler)
        right_layout.addWidget(self.sequence_viewer)

        # --- Splitter: sol panel / sağ panel ---
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.addWidget(self.left_panel)  # 🔹 artık self.left_panel
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([200, 800])

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

        # Header viewport'unun altına horizontal scrollbar yüksekliği kadar margin
        hsb_height = self.sequence_viewer.horizontalScrollBar().sizeHint().height()
        self.header_viewer.setViewportMargins(0, 0, 0, hsb_height)

        # Scroll senkronizasyonu
        self._sync_vertical_scrollbars()

    def _sync_vertical_scrollbars(self) -> None:
        h_vsb: QScrollBar = self.header_viewer.verticalScrollBar()
        s_vsb: QScrollBar = self.sequence_viewer.verticalScrollBar()

        s_vsb.valueChanged.connect(h_vsb.setValue)
        h_vsb.valueChanged.connect(s_vsb.setValue)

    def _on_splitter_moved(self, pos: int, index: int) -> None:
        """
        Splitter sürüklendiğinde sol panelin (header tarafı) genişliğini
        header_viewer'ın gösterebileceği maksimum genişlikle sınırla.
        """
        sizes = self.splitter.sizes()
        if len(sizes) < 2:
            return

        left = sizes[0]
        right = sizes[1]

        # Header'ların tam görünmesi için gereken maksimum genişlik
        if self.header_viewer.header_items:
            required = self.header_viewer.compute_required_width()
        else:
            required = left  # header yoksa kısıtlama yok

        # Sol panel limitin üstüne çıktıysa geri çek
        if left > required:
            total = left + right
            left = required
            right = max(0, total - left)

            # Sinyal döngüsüne girmemek için bloklayarak ayarla
            self.splitter.blockSignals(True)
            self.splitter.setSizes([left, right])
            self.splitter.blockSignals(False)

    def _update_header_max_width(self) -> None:
        """
        Header metinlerinin tamamını göstermek için gereken maksimum genişliği
        hesaplar ve sol paneli (left_panel) buna göre sınırlar.
        """
        if self.header_viewer.header_items:
            required = self.header_viewer.compute_required_width()
            # Hem header_viewer hem de sol panel bu değerden büyük olmasın:
            self.header_viewer.setMaximumWidth(required)
            self.left_panel.setMaximumWidth(required)
        else:
            # Hiç header yoksa kısıtlama yapma
            big = 16777215
            self.header_viewer.setMaximumWidth(big)
            self.left_panel.setMaximumWidth(big)

    def add_sequence(self, header: str, sequence: str) -> None:
        self.header_viewer.add_header(header)
        self.sequence_viewer.add_sequence(sequence)
        self.ruler.update()

        # 🔹 En uzun header değişmiş olabilir, max genişliği yeniden hesapla
        self._update_header_max_width() 
        
    def clear(self) -> None:
        self.header_viewer.clear()
        self.sequence_viewer.clear()
        self.ruler.update()
