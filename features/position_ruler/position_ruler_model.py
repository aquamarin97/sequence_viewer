# msa_viewer/position_ruler/position_ruler_model.py

from dataclasses import dataclass
from typing import Optional, List, Tuple
import math


@dataclass
class PositionRulerLayout:
    """
    Modelin paintEvent'e verdiği layout bilgisi.
    QPainter tarafı bu veriyi kullanarak çizim yapar.
    """
    max_len: int
    first_pos: int          # ekranda görünen ilk nt (1-based)
    last_pos: int           # ekranda görünen son nt (1-based)
    visible_span: int       # last_pos - first_pos + 1
    step: int               # ana tick label aralığı (örn. 10, 50, 100, 1000...)
    sel_start_pos: Optional[int]  # seçili aralığın başlangıcı (1-based)
    sel_end_pos: Optional[int]    # seçili aralığın sonu (1-based)
    special_positions: List[int]  # highlight edilecek özel nt pozisyonları (1-based)


class PositionRulerModel:
    """
    Position ruler için Model katmanı.

    Sorumluluklar:
    - Viewer'dan gelen:
        * max_sequence_length
        * view_left (scene px)
        * view_width (scene px)
        * char_width (px/nt)
        * selection_cols (0-based sütun aralığı)
      bilgilerini tutmak
    - Bu bilgilere göre:
        * Görünen nt aralığını (first_pos, last_pos)
        * Uygun tick step değerini
        * Seçili pozisyonları (nt olarak 1-based)
      hesaplamak.
    """

    def __init__(self) -> None:
        self.max_sequence_length: int = 0
        self.view_left: float = 0.0       # scene koordinatında sol
        self.view_width: float = 0.0      # scene koordinatında viewport genişliği
        self.char_width: float = 1.0
        self.selection_cols: Optional[Tuple[int, int]] = None

    # ------------------------------------------------------------------
    # State güncelleme
    # ------------------------------------------------------------------

    def set_state(
        self,
        *,
        max_len: int,
        view_left: float,
        view_width: float,
        char_width: float,
        selection_cols: Optional[Tuple[int, int]],
    ) -> None:
        self.max_sequence_length = max_len
        self.view_left = max(view_left, 0.0)
        self.view_width = max(view_width, 0.0)
        self.char_width = max(char_width, 0.0)
        self.selection_cols = selection_cols

    # ------------------------------------------------------------------
    # Layout hesaplama
    # ------------------------------------------------------------------

    def compute_layout(self) -> Optional[PositionRulerLayout]:
        """
        Şu anki state'e göre draw için gerekli layout'u hesaplar.
        Geçerli bir layout yoksa (örneğin max_len=0) None döner.
        """
        max_len = self.max_sequence_length
        if max_len <= 0:
            return None

        if self.view_width <= 0 or self.char_width <= 0:
            return None

        # Görünen sütun aralığı (0-based)
        first_col = int(math.floor(self.view_left / self.char_width))
        last_col = int(math.ceil((self.view_left + self.view_width) / self.char_width))

        first_col = max(0, first_col)
        last_col = min(max_len, last_col)

        if last_col <= first_col:
            return None

        first_pos = first_col + 1          # 1-based
        last_pos = last_col                # 1-based

        visible_span = last_pos - first_pos + 1
        if visible_span <= 0:
            return None

        step = self._choose_step_for_zoom(self.char_width, visible_span)

        # Seçili pozisyonlar (1-based)
        sel_start_pos: Optional[int] = None
        sel_end_pos: Optional[int] = None
        if self.selection_cols is not None:
            s, e = self.selection_cols
            if s > e:
                s, e = e, s
            sel_start_pos = s + 1
            sel_end_pos = e + 1

        special_positions: List[int] = []
        if sel_start_pos is not None:
            special_positions.append(sel_start_pos)
            if sel_end_pos is not None and sel_end_pos != sel_start_pos:
                special_positions.append(sel_end_pos)

        return PositionRulerLayout(
            max_len=max_len,
            first_pos=first_pos,
            last_pos=last_pos,
            visible_span=visible_span,
            step=step,
            sel_start_pos=sel_start_pos,
            sel_end_pos=sel_end_pos,
            special_positions=special_positions,
        )

    # ------------------------------------------------------------------
    # Tick aralığı seçimi (eski _choose_step_for_zoom + _round_to_nice_large)
    # ------------------------------------------------------------------

    def _choose_step_for_zoom(self, char_width: float, visible_span: int) -> int:
        """
        Görünen nt aralığına ve zoom seviyesine göre "güzel" tick/label aralığı seçer.
        char_width şu an için mantıkta kullanılmıyor ama geleceğe dönük parametre olarak bırakıldı.
        """
        if visible_span <= 0:
            return 1

        # 1. Temel hedef: ekranda yaklaşık 8–12 ana label olsun
        target_labels = 10.0
        raw_step = visible_span / target_labels

        if raw_step <= 1:
            return 1

        power = 10 ** int(math.floor(math.log10(raw_step)))
        base = raw_step / power

        if base <= 1.5:
            nice = 1
        elif base <= 3:
            nice = 2
        elif base <= 7:
            nice = 5
        else:
            nice = 10

        candidate = int(nice * power)

        # 3. Özel kurallar: çok büyük/küçük span'lerde daha seyrek/sık yap
        if visible_span >= 1_000_000:  # 1M+
            # Çok uzak zoom → 100K, 200K, 500K, 1M gibi
            candidate = self._round_to_nice_large(candidate)
        elif visible_span >= 100_000:  # 100K–1M
            candidate = max(candidate, 10_000)
        elif visible_span <= 100:  # Çok yakın zoom
            candidate = min(candidate, 10)

        return max(candidate, 1)

    def _round_to_nice_large(self, step: int) -> int:
        """
        1M+ görünürken daha güzel aralıklar: 100K, 200K, 500K, 1M, 2M, 5M...
        """
        if step < 100_000:
            return 100_000
        elif step <= 200_000:
            return 200_000
        elif step <= 500_000:
            return 500_000
        elif step <= 1_000_000:
            return 1_000_000
        elif step <= 2_000_000:
            return 2_000_000
        elif step <= 5_000_000:
            return 5_000_000
        else:
            # 10M, 20M, 50M...
            power = 10 ** int(math.log10(step))
            base = step // power
            if base <= 2:
                return 2 * power
            elif base <= 5:
                return 5 * power
            else:
                return 10 * power
