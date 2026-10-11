"""Execute unchanged calculation cells at a pinned commit (skip unrelated plots/system sizing)."""
from pathlib import Path
import argparse,json,hashlib,math,time,platform
from importlib.metadata import version
COMMIT='94247560a667905bfbf67e45a58965a58254fce8'
CASES={'water':('docs/examples/air_cooling_coil/air_cooling_coil_01.ipynb',[0,5,7,9,11,13,14,16]),
 'evaporator':('docs/examples/vapor_compression/ex02_air_evaporator.ipynb',[2,4,7,9,13,15,17]),
 'condenser':('docs/examples/vapor_compression/ex03_air_condenser.ipynb',[2,4,7,9,13,15,17,19])}
SAVED={'water':{'heat_transfer_w':4084.,'air_out_t_c':15.92,'fluid_out_t_c':11.11,'air_pressure_drop_pa':13.048,'fluid_pressure_drop_pa':774.812},
 'evaporator':{'heat_transfer_w':5915.,'air_out_t_c':13.1,'fluid_mass_flow_kg_h':142.096,'air_pressure_drop_pa':46.},
 'condenser':{'heat_transfer_w':7635.,'air_out_t_c':44.9,'fluid_out_t_c':45.83,'subcooling_k':4.17,'air_pressure_drop_pa':39.540}}


def q(value,unit):
    result=float(value.to(unit).m)
    if not math.isfinite(result):raise ValueError('Nonfinite upstream calculation: '+unit)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('kind',choices=CASES);parser.add_argument('--output',required=True);parser.add_argument('--source',required=True);args=parser.parse_args()
    SOURCE=Path(args.source).resolve()
    import hvac
    if not Path(hvac.__file__).resolve().is_relative_to(SOURCE):raise ValueError('Installed hvac must come from specified pinned source, not another package')
    ledger=json.loads((Path(__file__).parent/'source-tree.json').read_text(encoding='utf8'))
    for entry in ledger['files']:
        data=(SOURCE/entry['path']).read_bytes()
        assert hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()==entry['sha'],entry['path']
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    path,indices=CASES[args.kind];notebook=SOURCE/path;start=time.monotonic()
    record={'kind':args.kind,'status':'running','source_commit':COMMIT,'notebook':path,
        'notebook_sha256':hashlib.sha256(notebook.read_bytes()).hexdigest(),'executed_cells':indices,
        'evidence_kind':'software_reference_not_measured','notebook_inputs_modified':False,
        'dependency_versions':{p:version(p) for p in ('python-hvac','CoolProp','numpy','scipy','pint')},'python':platform.python_version(),
        'notebook_saved_rounded_outputs':SAVED[args.kind],'warning_policy':'unchanged upstream cells suppress CoolPropWarning'}
    try:
        cells=json.loads(notebook.read_text(encoding='utf8'))['cells'];scope={'__name__':'__reference_example__'}
        for i in indices:
            assert cells[i]['cell_type']=='code';exec(compile(''.join(cells[i]['source']),path+f':cell{i}','exec'),scope)
        if args.kind=='water':
            obj=scope['air_coil'];r=scope['result'];airin=scope['air_in'];airout=r['air_out'];fin=scope['water_in'];fout=r['water_out']
            ma=scope['air_m_dot'];mf=scope['water_m_dot'];power=r['Q_dot'];dpair=r['dP_air'];g=obj.core.geometry
            extra={'fluid_pressure_drop_pa':q(r['dP_water'],'Pa'),'surface_condition':r['air_surface_condition'],'ua_w_k':q(obj.core.UA,'W/K')}
        elif args.kind=='evaporator':
            obj=scope['evp'];airin=obj.air_in;airout=obj.air_out;fin=scope['evp_rfg_in'];fout=obj.rfg_out
            ma=obj.air_m_dot;mf=scope['rfg_m_dot'];power=obj.Q_dot;dpair=obj.air_dP;g=obj.geometry
            extra={'superheat_k':10.,'fluid_pressure_drop_pa':None,'fluid_pressure_drop_scope':'upstream constant-pressure model; not a computed zero'}
        else:
            obj=scope['condenser'];airin=scope['air_in'];airout=scope['air_out'];fin=scope['rfg_in'];fout=scope['rfg_out']
            ma=scope['air_m_dot'];mf=scope['rfg_m_dot'];power=obj.Q_dot;dpair=obj.air_dP;g=obj.geometry
            extra={'subcooling_k':q(obj.dT_sc,'K'),'fluid_pressure_drop_pa':None,'fluid_pressure_drop_scope':'upstream constant-pressure model; not a computed zero'}
        result={'heat_transfer_w':q(power,'W'),'air_out_t_c':q(airout.Tdb,'degC'),'air_out_relative_humidity':q(airout.RH,'frac'),
                'air_out_h_j_kg':q(airout.h,'J/kg'),'air_out_w_kg_kg':q(airout.W,'kg/kg'),'fluid_out_t_c':q(fout.T,'degC'),
                'fluid_out_h_j_kg':q(fout.h,'J/kg'),'fluid_mass_flow_kg_h':q(mf,'kg/hr'),'air_pressure_drop_pa':q(dpair,'Pa'),**extra}
        inputs={'air_t_c':q(airin.Tdb,'degC'),'air_relative_humidity':q(airin.RH,'frac'),'air_pressure_pa':q(airin.P,'Pa'),
            'air_dry_mass_flow_kg_s':q(ma,'kg/s'),'air_actual_volume_flow_m3_h':q(ma/airin.rho,'m^3/hr'),
            'fluid_in_t_c':q(fin.T,'degC'),'fluid_in_pressure_pa':q(fin.P,'Pa'),'fluid_in_h_j_kg':q(fin.h,'J/kg'),'fluid_mass_flow_kg_s':q(mf,'kg/s')}
        geometry={'face_width_m':q(g.width,'m'),'face_height_m':q(g.height,'m'),'rows':float(g.num_rows),
            'transverse_pitch_m':q(g.pitch_trv,'m'),'longitudinal_pitch_m':q(g.pitch_lon,'m'),
            'tube_od_m':q(g.d_o,'m'),'tube_id_m':q(g.d_i,'m'),'fin_thickness_m':q(g.t_fin,'m'),
            'fin_pitch_m':q(1/g.fin_density,'m'),'fin_conductivity_w_m_k':q(g.k_fin,'W/(m*K)'),
            'effective_total_tubes':float(g.num_tubes),'effective_tubes_first_row':float(g.num_tubes_1st_row),
            'tube_inventory_scope':'upstream continuous staggered-bank effective tube count, not an explicit integer tube network'}
        fluid_q=q(mf*(fout.h-fin.h),'W');air_q=q(ma*(airin.h-airout.h),'W')
        sign=-1 if args.kind=='condenser' else 1
        record.update(status='completed',computed=result,normalized_boundaries=inputs,geometry=geometry,
            energy_diagnostics={'fluid_enthalpy_power_magnitude_w':sign*fluid_q,'air_enthalpy_power_magnitude_w':sign*air_q},
            differences_from_saved_rounding={k:result[k]-v for k,v in SAVED[args.kind].items()})
    except Exception as exc:record.update(status='failed',error=f'{type(exc).__name__}: {exc}');raise
    finally:
        record['elapsed_s']=time.monotonic()-start;output.write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')


if __name__=='__main__':main()
