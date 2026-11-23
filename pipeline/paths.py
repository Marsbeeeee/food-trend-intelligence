"""Repository paths and read-only resolution of frozen historical template references."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def template_path(value=None):
    path=ROOT/(value or 'templates/weekly_report.md')
    if path.is_file():return path
    if value=='视频热点情报周报_母版.md':return ROOT/'templates/weekly_report.md'
    raise FileNotFoundError(path)
