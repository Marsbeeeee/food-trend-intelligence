"""Current account-first entry point."""
import argparse
import subprocess
import sys
from pipeline.paths import ROOT


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ('-h', '--help'):
        p = argparse.ArgumentParser(description='Discover accounts, review, then compare videos.')
        p.add_argument('action', choices=['accounts', 'videos', 'export', 'test'])
        p.print_help()
        return
    if argv[0] in ('accounts', 'videos'):
        from pipeline.benchmarks import main as invoke
        return invoke(argv)
    if argv[0] == 'export':
        from pipeline.export import main as invoke
        return invoke(argv[1:])
    if argv[0] == 'test':
        if len(argv) != 1:
            raise SystemExit('test takes no extra arguments')
        raise SystemExit(subprocess.call([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py'], cwd=ROOT))
    raise SystemExit('Video-first command retired. Use accounts --help, then videos --help.')

