"""Run the versioned export pipeline without network access."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--run-root', type=Path, default=ROOT / 'data/runs')
    parser.add_argument('--config', type=Path, default=ROOT / 'config/weekly.json')
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in ('.', '..'):
        parser.error('run-id must be a single directory name')
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    if cfg['filter_version'] != '1.0.0':
        parser.error('Unsupported filter version')
    subprocess.run([sys.executable, str(ROOT / 'pipeline/engine.py'), '--input-root', str(args.input_root.resolve()), '--run-root', str(args.run_root.resolve()), '--run-id', args.run_id, '--config', str(args.config.resolve())], check=True)
    run = args.run_root / args.run_id
    screened = [json.loads(s) for s in (run / 'screened_candidates.jsonl').read_text(encoding='utf-8').splitlines()]
    (run / 'excluded.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in screened if r['decision'] == 'exclude'), encoding='utf-8')
    sections = ['01｜本周情报摘要', '02｜美食与甜品趋势', '03｜视频形式与传播玩法', '04｜代表案例与对标账号观察', '05｜跨周观察与持续关注', '06｜完整热点情报明细（报告内置档案）', '07｜信息核验与采集规则（固定附页）', '08｜发布前检查与归档']
    text = '# 视频热点情报周报（固定样本测试版）\n\n'
    bodies = ['本次为固定导出测试，已确认独立热点 0 个。\n\n' + (run / 'weekly_report.md').read_text(encoding='utf-8'), '未完成话题核验，不确认趋势。', '未完整观看视频或取得字幕，形式观察未获取。', '详见 verified_cases.json；当前独立运行不沿用历史人工核验。', '缺少可比历史快照，变化无法判断。', '正式热点 0 个；候选详见 screened_candidates.jsonl。', '筛选规则由版本化代码和配置决定，未知指标为 null；保留来源行与哈希。', '本地流程已执行；原帖核验和人工审核未完成，不作正式发布。']
    for title, body in zip(sections, bodies):
        text += f'## {title}\n\n{body}\n\n'
    (run / 'report.md').write_text(text, encoding='utf-8')

if __name__ == '__main__':
    main()
