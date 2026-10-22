"""Model coverage lists (interface contract v1, section 3.1; spec E1).

Every result states what is included, excluded, extrapolated and degraded.  Ids are stable; new ids
may be appended, existing ids are never renamed.
"""
from __future__ import annotations

LABELS = {
    # included
    'air_core_friction': '空气侧芯体摩擦（干表面关联式 f）',
    'air_entrance_exit': '空气侧进/出口局部损失（已含在关联式 f 中，未重复计入）',
    'air_acceleration': '空气侧加速/减速压降（Kays–London 动量项）',
    'air_wet_increment': '空气侧湿附加压降（湿工况关联式 f 与干工况 f 之差，按湿面积占比加权）',
    'circuit_friction': '回路内摩擦压降', 'circuit_momentum': '回路内动量压降', 'return_bend': '回弯等效长度压降',
    'inlet_fittings': '进口端部附件', 'outlet_fittings': '出口端部附件', 'distributor': '分液器', 'capillaries': '毛细管',
    'outlet_header': '集气管/集水管', 'water_header': '水侧集管与进出口',
    'water_straight_friction': '水侧直管摩擦压降',
    'distributor_uniform_quality': '假设：分液器各支路出口干度均匀',
    # excluded
    'gravity_static': '重力静压（本轮不计）', 'fan_curve_coupling': '风机曲线耦合（本轮不做）',
    'frost_transient': '霜层生长与融霜（本轮不做）', 'bend_geometry': '折弯形状对换热与风阻的影响（本轮不做）',
    'contact_resistance_not_given': '翅片-管接触热阻（未输入，按理想接触）',
    'legacy_scope_pressure_terms': '旧口径（legacy_v0）：未含空气加速项、湿附加压降及新增附件压降',
    'pressure_not_modelled_input_ua': '输入 UA 模式不计算压降',
    'air_pressure_not_modelled': '本模型不计算空气压降',
    # extrapolated
    'rows_saturate_at_6': '排数 > 6：按声明逐排饱和外推',
    'plain_fin_pitch_gt_8_7mm': '平片片距 > 8.7 mm：按声明外推',
    'correlation_range_tolerance': '几何边界按声明容差（≤ 1%）外推',
    # degraded
    'default_subcooling_5k': '入口状态使用默认过冷度 5 K', 'accessory_rated_point_scaling': '附件压降按额定点换算',
    'accessory_not_computed': '附件压降未计算（无几何、无额定点）', 'louver_geometry_interval': '百叶几何未知，按区间输出',
    'wet_increment_not_computed': '湿工况附加压降未计算',
}


def item(ident, source=None, detail=None):
    if ident not in LABELS:
        raise KeyError(f'unknown coverage id {ident}')
    out = {'id': ident, 'label_zh': LABELS[ident], 'source': source}
    if detail is not None:
        out['detail'] = detail
    return out


def coverage(included=(), excluded=(), extrapolated=(), degraded=()):
    return {'included': list(included), 'excluded': list(excluded), 'extrapolated': list(extrapolated),
            'degraded': list(degraded)}


def pressure_scope(case: dict) -> str:
    return case.get('model', {}).get('pressure_scope', 'legacy_v0')
