"""Single command router. Optional export dependencies load only when requested."""
import argparse,sys,subprocess
from pipeline.paths import ROOT
def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    actions=['collect','discovery','screen','verify','report','review-report','export','test']
    if not argv or argv[0] in ('-h','--help'):
        p=argparse.ArgumentParser(description='Food video workflow: one stage at a time. Video publication dates are unrestricted.')
        p.add_argument('action',choices=actions);p.print_help();return
    action=argv[0]
    if action=='collect':
        from pipeline.collection import main as invoke
    elif action=='review-report':
        from pipeline.report_draft import main as invoke
    elif action=='export':
        from pipeline.export import main as invoke
    elif action=='test':
        if len(argv)>1:raise SystemExit('test takes no extra arguments')
        raise SystemExit(subprocess.call([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py'],cwd=ROOT))
    elif action in ('discovery','screen','verify','report'):
        from pipeline.workflow import main as invoke
        return invoke(argv)
    else:raise SystemExit('Unknown action: '+action)
    return invoke(argv[1:])
