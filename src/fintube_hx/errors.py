"""Structured model-range errors (interface contract v1, section 4).

``ModelRangeError`` is a ``ValueError``: existing ``except ValueError`` handlers keep working.
``str(exc)`` is the complete Chinese explanation (``message_zh``); when an older English message
existed, it is kept in ``message_en`` and appended in parentheses so that logs remain searchable.
``fallbacks`` lists explicit, user-confirmed alternatives; a caller may only apply ``patch`` after
the user agrees (nothing is applied silently).
"""
from __future__ import annotations

PLANNED_NOTE = '本版本不支持，规划中'


class ModelRangeError(ValueError):
    def __init__(self, message_zh, *, field=None, value=None, allowed=None, source=None,
                 fallbacks=(), message_en=None):
        self.message_zh = message_zh + (f'（{message_en}）' if message_en else '')
        self.message_en = message_en
        self.field, self.value, self.allowed, self.source = field, value, allowed, source
        self.fallbacks = [dict(f) for f in fallbacks]
        super().__init__(self.message_zh)

    def to_dict(self):
        return {'type': type(self).__name__, 'field': self.field, 'value': self.value, 'allowed': self.allowed,
                'source': self.source, 'fallbacks': self.fallbacks, 'message_zh': self.message_zh,
                'message_en': self.message_en}


class UnsupportedFeatureError(ModelRangeError, NotImplementedError):
    """A capability outside this version (C5); also a NotImplementedError for older callers."""


def fallback(ident, label_zh, patch=None):
    return {'id': ident, 'label_zh': label_zh, 'patch': dict(patch or {})}


# correlation parameter -> (Chinese name, input field that controls it)
PARAMETER_FIELDS = {
    'Re': ('空气侧雷诺数 Re_Dc', 'air.volume_flow_m3_h'),
    'collar diameter': ('套管外径 Dc', 'geometry.tube_outer_diameter_m'),
    'hydraulic diameter': ('水力直径 Dh', 'geometry.fin_pitch_m'),
    'transverse pitch': ('横向管距 Pt', 'geometry.transverse_pitch_m'),
    'longitudinal pitch': ('纵向管距 Pl', 'geometry.longitudinal_pitch_m'),
    'fin pitch': ('片距 Fp', 'geometry.fin_pitch_m'),
    'rows': ('排数 N', 'geometry.rows'),
    'louver height': ('百叶高度 Lh', 'geometry.louver_height_m'),
    'louver pitch': ('百叶间距 Lp', 'geometry.louver_pitch_m'),
    'louver height/pitch': ('百叶高距比 Lh/Lp', 'geometry.louver_height_m'),
    'corrugation angle deg': ('波纹角 θ', 'geometry.wave_height_m'),
    'projected wave length': ('波纹投影长度 Xf', 'geometry.wave_projected_length_m'),
    'wave height': ('波高 Pd', 'geometry.wave_height_m'),
}
ROW_EXTRAPOLATION_MAX_ROWS = 12
PLAIN_FIN_PITCH_EXTRAPOLATION_MAX_M = 0.012
# Declared wet-friction fin-pitch extrapolation (Wang, Lin & Lee 2000 sample: 1.19..3.2 mm; core 0.1.0.dev18).
# 4.0 mm = +25 % on the published bound, more conservative than the dry plain-fin +38 % (8.7 -> 12 mm): 31 wet samples
# and an exponent with (Fp/Pl)^2.5 * ln(9 Re_film).  Only the fin pitch is extended.
WET_FRICTION_FIN_PITCH_PUBLISHED_MAX_M = 0.0032
WET_FRICTION_FIN_PITCH_EXTRAPOLATION_MAX_M = 0.004


def range_error(correlation, parameter, value, lo, hi, *, message_en=None, source=None, fin_type=None):
    """Structured error for a value outside a correlation's published sample range."""
    name, field = PARAMETER_FIELDS.get(parameter, (parameter, None))
    text = f'{correlation} 的{name} = {value:g} 超出原文样本范围 [{lo:g}, {hi:g}]，不能计算'
    fallbacks = []
    if parameter == 'collar diameter' and value < lo:
        text += f'。小管径（Dc < {lo * 1000:g} mm）{PLANNED_NOTE}'
        return UnsupportedFeatureError(text, field=field, value=value, allowed={'min': lo, 'max': hi}, source=source,
                                       message_en=message_en)
    if parameter == 'rows' and hi < value <= ROW_EXTRAPOLATION_MAX_ROWS:
        fallbacks.append(fallback('declare_row_extrapolation', '声明排数外推（仅逐管网络；结果标注，不计入验收）',
                                  {'geometry.row_extrapolation': 'saturate_at_row_6'}))
    if (fin_type == 'plain' and parameter in ('fin pitch', 'hydraulic diameter') and value > hi
            and (parameter == 'hydraulic diameter' or value <= PLAIN_FIN_PITCH_EXTRAPOLATION_MAX_M)):
        fallbacks.append(fallback('declare_fin_pitch_extrapolation',
                                  '声明平片大片距外推（片距≤ 12 mm；结果标注，不计入验收）',
                                  {'geometry.fin_pitch_extrapolation': True}))
    return ModelRangeError(text, field=field, value=value, allowed={'min': lo, 'max': hi}, source=source,
                           fallbacks=fallbacks, message_en=message_en)


SWITCH_TO_V1 = fallback('switch_pressure_scope_v1', '切换到 v1 压降口径（旧项目口径不含该字段）', {'model.pressure_scope': 'v1'})
