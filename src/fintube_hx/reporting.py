"""Public baseline summaries and safe literal CSV text."""


def summary_record(result):
    if 'error' in result:
        row={'case':result.get('case_name','failed'),'kind':result.get('kind','unknown'),'converged':False,'error':result['error'],'verification_level':'failed_not_validated'}
    else:
        geometry=result.get('geometry_model',{});target=result.get('target_solution',{})
        row={'case':result['case_name'],'kind':result['kind'],'heat_transfer_w':result['heat_transfer_w'],
             'air_out_t_c':result['air_out']['t_db_c'],'air_out_relative_humidity':result['air_out']['relative_humidity'],
             'fluid_out_t_c':result['fluid_out']['temperature_c'],'fluid_mass_flow_kg_s':result['fluid_out']['mass_flow_kg_s'],
             'condensate_kg_s':result['condensate_kg_s'],'balance_relative_error':result['energy_balance_relative_error'],
             'converged':result['converged'],'verification_level':result['verification_level'],'model_version':result['model_version'],
             'source_kind':result['provenance']['source_kind'],'ua_w_k':result.get('ua_w_k',result['inputs']['model'].get('ua_w_k')),
             'air_core_friction_pressure_drop_pa':geometry.get('air_core_friction_pressure_drop_pa'),
             'water_straight_tube_pressure_drop_pa':geometry.get('water_straight_tube_pressure_drop_pa'),
             'target_cold_verified':target.get('cold_verified'),'target_residual_k':target.get('residual_k')}
    if 'scan' in result:row.update(scan_parameter=result['scan']['parameter'],scan_value=result['scan']['value'])
    return row


def safe_csv_value(value):
    return "'"+value if isinstance(value,str) and value.startswith(('=','+','-','@','\t','\r')) else value
