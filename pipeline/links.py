"""Stable content links; original observation URLs remain unchanged."""
from urllib.parse import urlsplit,urlunsplit,parse_qs
import re
def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))



def video_url(row):
    u=urlsplit(row['url'])
    domains={'douyin':('douyin.com',),'bilibili':('bilibili.com','b23.tv'),'xiaohongshu':('xiaohongshu.com','xhslink.com')}[row['platform']]
    if u.scheme!='https' or u.username or u.password or not any(u.hostname==d or (u.hostname or '').endswith('.'+d) for d in domains):raise ValueError('Unexpected source URL')
    if row['platform']=='douyin':
        modal=parse_qs(u.query,keep_blank_values=True).get('modal_id')
        match=re.fullmatch(r'/video/(\d+)/?',u.path)
        source_id=modal[0] if modal else match[1] if match else None
        if source_id!=row['content_id'] or not re.fullmatch(r'\d{10,25}',row['content_id']):raise ValueError('Douyin URL identity mismatch')
        return 'https://www.douyin.com/video/'+row['content_id']
    return row['url']

