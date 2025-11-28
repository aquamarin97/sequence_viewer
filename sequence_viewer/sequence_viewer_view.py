# msa_viewer/sequence_viewer/sequence_viewer_view.py

from typing import List, Optional, Tuple, Any

from PyQt5.QtCore import Qt, QPointF, QEasingCurve, QVariantAnimation
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QScrollBar

from graphics.sequence_item import SequenceGraphicsItem


class SequenceViewerView(QGraphicsView):
    """
    Sadece sekansları çizen, düşük seviye QGraphicsView katmanı.

    CMV ayrımı:
    - Model  : SequenceViewerModel (sekans verisi, seçim state'i)
    - View   : Bu sınıf (scene + SequenceGraphicsItem çizimi / layout)
    - Control: SequenceViewerController (event handling, zoom/selection mantığı)

    Bu sınıf:
    - Scene ve SequenceGraphicsItem'ları yönetir
    - Zoom geometri/animasyon mantığını içerir
    - Seçimin görsel highlight'ını uygular
    - Mouse / wheel event'lerini opsiyonel olarak controller'a delege eder
    """

    def __init__(
        self,
        parent=None,
        *,
        char_width: float = 12.0,
        char_height: float = 18.0,
    ) -> None:
        super().__init__(parent)

        # Scene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Geometri / layout
        self.char_width: float = float(char_width)
        self.char_height: int = int(round(char_height))
        self.trailing_padding_line_px: float = 80.0
        self.trailing_padding_text_px: float = 30.0

        # En uzun sekans boyu (SequenceGraphicsItem.sequence üzerinden hesaplanır)
        self.max_sequence_length: int = 0

        # Items
        self.sequence_items: List[SequenceGraphicsItem] = []

        # Zoom animasyonu
        self._zoom_animation = QVariantAnimation(self)
        self._zoom_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._zoom_animation.valueChanged.connect(self._on_zoom_value_changed)

        self._zoom_center_nt: Optional[float] = None
        self._zoom_view_width_px: Optional[float] = None

        # View ayarları
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Controller referansı (SequenceViewerController ile bağlanacak)
        self._controller: Optional[Any] = None

    # ---------------------------------------------------------------------
    # Controller bağlantısı
    # ---------------------------------------------------------------------

    def set_controller(self, controller: Any) -> None:
        """
        SequenceViewerController örneğini view ile ilişkilendir.
        Event yönlendirmesi / yüksek seviye işlemler için kullanılır.
        """
        self._controller = controller

    # ---------------------------------------------------------------------
    # Public API: item yönetimi
    # ---------------------------------------------------------------------

    def add_sequence_item(self, sequence_string: str) -> SequenceGraphicsItem:
        """
        Verilen sekans için yeni bir SequenceGraphicsItem oluşturup scene'e ekler.
        Satır indeksi, mevcut item sayısına göre belirlenir.
        """
        row_index = len(self.sequence_items)
        item = SequenceGraphicsItem(
            sequence=sequence_string,
            char_width=self.char_width,
            char_height=self.char_height,
        )
        item.setPos(0, row_index * self.char_height)
        self.scene.addItem(item)
        self.sequence_items.append(item)
        self._update_scene_rect()
        return item

    def clear_items(self) -> None:
        """
        Tüm SequenceGraphicsItem'ları ve scene içeriğini temizler.
        """
        self.sequence_items.clear()
        self.scene.clear()
        self.max_sequence_length = 0
        self.scene.setSceneRect(0, 0, 0, 0)
        self.scene.invalidate()

    # ---------------------------------------------------------------------
    # Public API: geometri / zoom
    # ---------------------------------------------------------------------

    def current_char_width(self) -> float:
        """
        Anlık char_width değerini döndürür.
        Zoom animasyonu sırasında ara değeri döner.
        """
        return self._effective_char_width()

    def compute_min_char_width(self) -> float:
        """
        Viewport genişliğine ve en uzun sekans boyuna göre
        izin verilen minimum char_width değerini hesaplar.
        """
        if not self.sequence_items:
            return self.char_width

        max_len = self.max_sequence_length
        if max_len <= 0:
            return self.char_width

        viewport_width = self.viewport().width()
        if viewport_width <= 0:
            return self.char_width

        # LINE modunda padding daha geniş; en geniş padding'i baz al
        trailing_padding = max(
            self.trailing_padding_line_px,
            self._current_trailing_padding(),
        )

        available_width = viewport_width - trailing_padding
        if available_width <= 0:
            return 0.000001

        min_char_width = available_width / float(max_len)
        return max(min_char_width, 0.000001)

    def apply_char_width(
        self,
        new_char_width: float,
        center_nt: Optional[float] = None,
        view_width_px: Optional[float] = None,
    ) -> None:
        """
        View'daki tüm SequenceGraphicsItem'lara yeni char_width uygular
        ve gerekiyorsa verilen pivot nt etrafında yeniden merkezler.

        Genelde controller tarafından kullanılır.
        """
        if view_width_px is None:
            view_width_px = float(self.viewport().width())

        # char_width gerçekten değişmiyorsa ve pivot yoksa uğraşma
        if abs(new_char_width - self.char_width) < 0.0001 and center_nt is None:
            return

        # 1) Yeni char_width'ü uygula
        applied_width = float(new_char_width)
        for item in self.sequence_items:
            item.set_char_width(applied_width)

        # Item clamp/prepareGeometryChange sonrası gerçek değeri sakla
        if self.sequence_items:
            applied_width = float(self.sequence_items[0].char_width)
        self.char_width = applied_width
        self._update_scene_rect()

        # 2) Pivot nt etrafında yatayda yeniden merkezle
        if center_nt is not None:
            self._recenter_horizontally(center_nt, view_width_px)

        # LOD güncelle (view tarafında böyle bir fonksiyon tanımlıysa)
        if hasattr(self, "_update_lod_for_all_items"):
            # type: ignore[attr-defined]
            self._update_lod_for_all_items()

        self.viewport().update()

    def start_zoom_animation(
        self,
        target_char_width: float,
        center_nt: float,
        view_width_px: Optional[float] = None,
    ) -> None:
        """
        Controller'dan tetiklenen zoom animasyonu.
        """
        if view_width_px is None:
            view_width_px = float(self.viewport().width())

        current_char_width = self._get_current_char_width()

        # Hedefle mevcut aynıysa direkt uygula
        if abs(target_char_width - current_char_width) < 0.0001:
            self.apply_char_width(target_char_width, center_nt, view_width_px)
            return

        # Animasyon zaten çalışıyorsa:
        # - pivotu sabit tut (ilk başlatıldığında ne ise o),
        # - sadece yeni hedef genişliği güncelle.
        if self._zoom_animation.state() == QVariantAnimation.Running:
            self._zoom_view_width_px = view_width_px
            self._zoom_animation.setEndValue(target_char_width)
            return

        # Animasyon yeni başlıyorsa
        self._zoom_center_nt = center_nt
        self._zoom_view_width_px = view_width_px

        self._zoom_animation.setDuration(180)  # 140–200 ms arası gayet akıcı
        self._zoom_animation.setStartValue(current_char_width)
        self._zoom_animation.setEndValue(target_char_width)
        self._zoom_animation.start()

    def zoom_to_nt_range(self, start_nt: float, end_nt: float) -> None:
        """
        Cetvelden gelen 'nt aralığına zoom' isteği için saf geometri.
        Yüksek seviyede ruler/controller bu metodu çağırabilir.
        """
        if not self.sequence_items:
            return

        a = float(start_nt)
        b = float(end_nt)
        if a == b:
            span_nt = 1.0
            center_nt = a
        else:
            left_nt = min(a, b)
            right_nt = max(a, b)
            span_nt = max(right_nt - left_nt, 1.0)
            center_nt = (left_nt + right_nt) / 2.0

        viewport_width_px = float(self.viewport().width())
        if viewport_width_px <= 0:
            return

        desired_char_width = viewport_width_px / span_nt

        min_char_width = self.compute_min_char_width()
        max_char_width = 90.0
        new_char_width = max(min_char_width, min(desired_char_width, max_char_width))

        if abs(new_char_width - self.char_width) > 0.0001:
            self.char_width = new_char_width
            for item in self.sequence_items:
                item.set_char_width(self.char_width)
            self._update_scene_rect()

        # Aynı yeniden merkezleme mantığını kullan
        self._recenter_horizontally(center_nt, viewport_width_px)
        self.viewport().update()

    # ---------------------------------------------------------------------
    # Public API: seçim çizimi
    # ---------------------------------------------------------------------

    def clear_visual_selection(self) -> None:
        """
        Model/controller seçim bilgisini temizlediğinde,
        view tarafındaki highlight'ları sıfırlamak için.
        """
        for item in self.sequence_items:
            item.clear_selection()
        self.viewport().update()

    def set_visual_selection(
        self,
        row_start: int,
        row_end: int,
        col_start: int,
        col_end: int,
    ) -> None:
        """
        Verilen satır / sütun aralığını highlight eder.
        Satır / sütun aralığı önceden controller/model tarafından clamp'lenmiş olmalı.
        """
        for row_index, item in enumerate(self.sequence_items):
            if row_start <= row_index <= row_end and col_start >= 0 and col_end >= 0:
                item.set_selection(col_start, col_end)
            else:
                item.clear_selection()
        self.viewport().update()

    # ---------------------------------------------------------------------
    # Yardımcılar: scene ve geometri
    # ---------------------------------------------------------------------

    def _update_scene_rect(self) -> None:
        """
        SequenceGraphicsItem'ların boyuna göre scene rect'i günceller.
        """
        if not self.sequence_items:
            self.scene.setSceneRect(0, 0, 0, 0)
            self.max_sequence_length = 0
            return

        max_len = max(len(item.sequence) for item in self.sequence_items)
        self.max_sequence_length = max_len
        trailing_padding = self._current_trailing_padding()

        width = max_len * self.char_width + trailing_padding
        height = len(self.sequence_items) * self.char_height
        self.scene.setSceneRect(0, 0, width, height)
        self.scene.invalidate()

    def _current_trailing_padding(self) -> float:
        """
        Display moduna göre sağdaki boşluk miktarını belirler.
        """
        if not self.sequence_items:
            return self.trailing_padding_text_px

        # Tüm satırlar aynı display_mode'u kullanıyor varsayımıyla ilk item yeterli
        first_item_mode = self.sequence_items[0].display_mode
        if first_item_mode == SequenceGraphicsItem.LINE_MODE:
            return self.trailing_padding_line_px

        # TEXT ve BOX modunda daha küçük padding
        return self.trailing_padding_text_px

    def _effective_char_width(self) -> float:
        """
        Zoom animasyonu sırasında ara değer, değilse gerçek uygulanan char_width.
        """
        if self._zoom_animation.state() == QVariantAnimation.Running:
            current_value = self._zoom_animation.currentValue()
            if current_value is not None:
                return float(current_value)

        if self.sequence_items:
            return float(self.sequence_items[0].char_width)

        return float(self.char_width)

    def _get_current_char_width(self) -> float:
        """
        Backward-compatible helper – dışarıdan current_char_width() kullanılabilir.
        """
        return self._effective_char_width()

    def _recenter_horizontally(
        self,
        center_nt: float,
        view_width_px: float,
    ) -> None:
        """
        Belirli bir nt'i viewport'un ortasında olacak şekilde yatay scroll ayarı yapar.
        """
        if view_width_px <= 0:
            view_width_px = float(self.viewport().width())
            if view_width_px <= 0:
                return

        scene_width = float(self.scene.sceneRect().width())
        if scene_width <= 0:
            return

        # nt aralığına clamp
        if self.max_sequence_length > 0:
            center_nt = max(0.0, min(center_nt, float(self.max_sequence_length)))

        cw = self._effective_char_width()
        center_x = center_nt * cw
        ideal_left = center_x - view_width_px / 2.0

        # Scene genişliğine göre clamp
        max_left = max(0.0, scene_width - view_width_px)
        ideal_left = max(0.0, min(ideal_left, max_left))

        hbar: QScrollBar = self.horizontalScrollBar()
        current_left = float(hbar.value())

        # Çok küçük farklar için setValue çağırma → 1px jitter'ı azaltır
        if abs(ideal_left - current_left) < 0.5:
            return

        hbar.setValue(int(round(ideal_left)))

    def _on_zoom_value_changed(self, value) -> None:
        """
        Zoom animasyonu her adımda çağrılır; ara char_width değeri uygular.
        """
        if self._zoom_center_nt is None or self._zoom_view_width_px is None:
            return

        try:
            new_char_width = float(value)
        except (TypeError, ValueError):
            return

        self.apply_char_width(
            new_char_width,
            self._zoom_center_nt,
            float(self._zoom_view_width_px),
        )

    # ---------------------------------------------------------------------
    # Koordinat dönüşümü (controller için)
    # ---------------------------------------------------------------------

    def scene_pos_to_row_col(self, scene_pos: QPointF) -> Tuple[int, int]:
        """
        Scene koordinatındaki bir noktayı, satır/sütun indeksine çevirir.
        Controller, mouse event'lerini modele çevirmek için bu metodu kullanır.
        """
        row = int(scene_pos.y() // self.char_height)

        current_cw = self._get_current_char_width()
        if current_cw <= 0:
            current_cw = self.char_width if self.char_width > 0 else 0.000001

        col = int(scene_pos.x() // current_cw)
        return row, col

    # ---------------------------------------------------------------------
    # Event yönlendirme
    # ---------------------------------------------------------------------

    def wheelEvent(self, event) -> None:
        """
        Yüksek seviye zoom/scroll davranışı controller tarafından
        yönetilsin diye event'i önce controller'a paslıyoruz.
        Controller None ise normal QGraphicsView davranışına döner.
        """
        if self._controller is not None:
            handled = getattr(self._controller, "handle_wheel_event", None)
            if callable(handled) and handled(event):
                return

        super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._controller is not None:
            handled = getattr(self._controller, "handle_mouse_press", None)
            if callable(handled) and handled(event):
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._controller is not None:
            handled = getattr(self._controller, "handle_mouse_move", None)
            if callable(handled) and handled(event):
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._controller is not None:
            handled = getattr(self._controller, "handle_mouse_release", None)
            if callable(handled) and handled(event):
                return
        super().mouseReleaseEvent(event)
