# msa_viewer/header_viewer/header_viewer_view.py

from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QFontMetrics
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene

from graphics.header_item.header_item import HeaderRowItem


class HeaderViewerView(QGraphicsView):
    """
    Sadece header satırlarını çizen view.

    CMV:
    - Model: HeaderViewerModel (header string listesi)
    - View : Bu sınıf (QGraphicsView + HeaderRowItem'lar)
    - Widget: HeaderViewerWidget (model + view'i bir araya getiren facade)

    SequenceViewerWidget ile aynı row_height kullanır,
    dikey scroll barlar dışarıdan (Workspace) senkronize edilir.
    """

    def __init__(
        self,
        parent=None,
        *,
        row_height: float = 18.0,
        initial_width: float = 160.0,
    ) -> None:
        super().__init__(parent)

        # Scene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Geometri
        self.row_height: int = int(round(row_height))
        self.header_width: float = float(initial_width)

        # Header item listesi
        self.header_items: List[HeaderRowItem] = []

        # View ayarları
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.setMinimumWidth(60)
        self.setMaximumWidth(400)

    # ------------------------------------------------------------------
    # Public API: item yönetimi
    # ------------------------------------------------------------------

    def add_header_item(self, display_text: str) -> HeaderRowItem:
        """
        Verilen display_text için yeni bir HeaderRowItem oluşturup scene'e ekler.
        Model tarafı ham metni tutar, bu metnin başına "1.", "2." vb. eklemek
        Widget/Controller seviyesinin işidir.
        """
        row_index = len(self.header_items)

        item_width = self.viewport().width() or self.header_width
        item = HeaderRowItem(
            text=display_text,
            width=item_width,
            row_height=self.row_height,
        )
        item.setPos(0, row_index * self.row_height)

        self.scene.addItem(item)
        self.header_items.append(item)

        self._update_scene_rect()
        return item

    def clear_items(self) -> None:
        """
        Tüm HeaderRowItem'ları ve scene içeriğini temizler.
        """
        self.header_items.clear()
        self.scene.clear()
        self._update_scene_rect()

    # ------------------------------------------------------------------
    # Geometri / scene rect
    # ------------------------------------------------------------------

    def _update_scene_rect(self) -> None:
        """
        Header satır sayısına göre scene rect'i günceller.
        """
        height = len(self.header_items) * self.row_height
        width = self.viewport().width() or self.header_width
        self.scene.setSceneRect(0, 0, width, height)

    def compute_required_width(self) -> int:
        """
        Header panelinin "maksimum mantıklı" genişliğini hesaplar.
        En uzun header FULL metninin piksel genişliği + padding + küçük buffer döner.
        """
        if not self.header_items:
            return 100  # fallback

        metrics = QFontMetrics(self.header_items[0].font)
        max_px = 0

        left_padding = 6
        right_padding = 4
        safety = 4   # 1–2 px’lik hesaplama farklarını tolere etmek için

        for item in self.header_items:
            # Önce full_text'i dene (eski API)
            if hasattr(item, "full_text"):
                text = item.full_text
            # Sonra text varsa onu dene (ileride eklenebilir)
            elif hasattr(item, "text"):
                text = item.text
            # Hiçbiri yoksa son çare: str(item)
            else:
                text = str(item)

            w = metrics.width(text)
            if w > max_px:
                max_px = w

        return max_px + left_padding + right_padding + safety


    # ------------------------------------------------------------------
    # Event: resize
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        """
        Header panelinin genişliği değiştiğinde:
        - Tüm item'ların width'ini günceller
        - Scene rect'i yeniden hesaplar
        - "Metin tam görünürse" max-width'i dinamik olarak ayarlar
        """
        super().resizeEvent(event)

        w = self.viewport().width()
        for item in self.header_items:
            item.set_width(w)
        self._update_scene_rect()

        # Dinamik max-width sınırı
        required = self.compute_required_width() if self.header_items else 10

        if w >= required:
            # Header metinlerinin tamamını gösterebildiğimiz noktaya geldik
            # → daha fazla büyümeye izin vermeyelim
            self.setMaximumWidth(required)
        else:
            # Henüz tam göstermiyorsa serbest büyüyebilsin
            # Qt'nin "sonsuz" default max'ına yakın büyük bir değer
            self.setMaximumWidth(16777215)
