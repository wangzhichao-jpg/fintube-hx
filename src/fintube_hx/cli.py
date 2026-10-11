"""Standalone public baseline CLI; no professional-only commands."""
import argparse
import csv
import json
from pathlib import Path
import sys
from .engine import run_case,capabilities
from .storage import load_case,save_json
from .reporting import summary_record,safe_csv_value


def export_csv(path,rows):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));writer.writeheader()
        writer.writerows([{k:safe_csv_value(v) for k,v in r.items()} for r in rows])


def main(argv=None):
    parser=argparse.ArgumentParser(description='Fintube HX Community：基础数值模型，未实测精度验证')
    subs=parser.add_subparsers(dest='command',required=True);subs.add_parser('capabilities',help='列出本版实际能力')
    run=subs.add_parser('run');run.add_argument('case');run.add_argument('--output',default='output/result.json');run.add_argument('--xlsx')
    batch=subs.add_parser('batch');batch.add_argument('cases',nargs='+');batch.add_argument('--output',default='output/batch.csv');batch.add_argument('--xlsx')
    scan=subs.add_parser('scan');scan.add_argument('case');scan.add_argument('--parameter',required=True);scan.add_argument('--values',required=True);scan.add_argument('--output',default='output/scan.json');scan.add_argument('--csv');scan.add_argument('--xlsx')
    args=parser.parse_args(argv)
    try:
        if args.command=='capabilities':print(json.dumps(capabilities(),ensure_ascii=False,indent=2));return 0
        if args.command=='run':
            r=run_case(load_case(args.case));save_json(args.output,r)
            if args.xlsx:
                from .spreadsheet import export_workbook
                export_workbook(args.xlsx,[r])
            print(json.dumps(summary_record(r),ensure_ascii=False,indent=2));return 0 if r['converged'] else 2
        if args.command=='scan':
            from .scan import scan_case
            values=json.loads(args.values,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Finite values required')))
            report=scan_case(load_case(args.case),args.parameter,values);save_json(args.output,report);results=report['results']
            if args.csv:export_csv(args.csv,[summary_record(r) for r in results])
        else:
            results=[]
            for filename in args.cases:
                case={}
                try:case=load_case(filename);results.append(run_case(case))
                except Exception as exc:results.append({'case_name':str(filename),'kind':case.get('kind','unknown'),'converged':False,'error':str(exc),'inputs':case})
            export_csv(args.output,[summary_record(r) for r in results])
        if args.xlsx:
            from .spreadsheet import export_workbook
            export_workbook(args.xlsx,results)
        return 0 if all(r['converged'] for r in results) else 2
    except Exception as exc:print('计算未完成：'+str(exc),file=sys.stderr);return 2
