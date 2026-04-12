# features/position_ruler/position_ruler_model.py
from dataclasses import dataclass
from typing import Optional, List, Tuple
import math

@dataclass
class PositionRulerLayout:
    max_len:int; first_pos:int; last_pos:int; visible_span:int; step:int
    sel_start_pos:Optional[int]; sel_end_pos:Optional[int]; special_positions:List[int]

class PositionRulerModel:
    def __init__(self):
        self.max_sequence_length=0; self.view_left=0.0; self.view_width=0.0
        self.char_width=1.0; self.selection_cols=None

    def set_state(self, *, max_len, view_left, view_width, char_width, selection_cols):
        self.max_sequence_length=max_len; self.view_left=max(view_left,0.0)
        self.view_width=max(view_width,0.0); self.char_width=max(char_width,0.0)
        self.selection_cols=selection_cols

    def compute_layout(self):
        max_len=self.max_sequence_length
        if max_len<=0 or self.view_width<=0 or self.char_width<=0: return None
        first_col=max(0,int(math.floor(self.view_left/self.char_width)))
        last_col=min(max_len,int(math.ceil((self.view_left+self.view_width)/self.char_width)))
        if last_col<=first_col: return None
        first_pos=first_col+1; last_pos=last_col; visible_span=last_pos-first_pos+1
        if visible_span<=0: return None
        step=self._choose_step(self.char_width,visible_span)
        sel_start=sel_end=None
        if self.selection_cols:
            s,e=self.selection_cols
            if s>e: s,e=e,s
            sel_start,sel_end=s+1,e+1
        specials=[]
        if sel_start is not None:
            specials.append(sel_start)
            if sel_end!=sel_start: specials.append(sel_end)
        return PositionRulerLayout(max_len=max_len,first_pos=first_pos,last_pos=last_pos,visible_span=visible_span,step=step,sel_start_pos=sel_start,sel_end_pos=sel_end,special_positions=specials)

    def _choose_step(self,char_width,visible_span):
        if visible_span<=0: return 1
        raw=visible_span/10.0
        if raw<=1: return 1
        power=10**int(math.floor(math.log10(raw))); base=raw/power
        nice=1 if base<=1.5 else 2 if base<=3 else 5 if base<=7 else 10
        cand=int(nice*power)
        if visible_span<=100: cand=min(cand,10)
        return max(cand,1)


