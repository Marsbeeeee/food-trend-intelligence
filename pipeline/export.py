"""Export the Markdown master to editable Word, optionally PDF via LibreOffice.

No browser automation, remote upload, or source-data changes occur here.
"""
from pathlib import Path
import argparse,json,shutil,subprocess,tempfile,os

def export_docx(source,dest):
    import re,html,json
    from docx import Document
    from docx.shared import Inches,Pt,RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.section import WD_SECTION_START,WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
    from docx.opc.constants import RELATIONSHIP_TYPE

    text=source.read_text(encoding='utf-8-sig');doc=Document()
    sec=doc.sections[0];sec.page_width=Inches(8.5);sec.page_height=Inches(11)
    sec.top_margin=Inches(.65);sec.bottom_margin=Inches(.65);sec.left_margin=Inches(.72);sec.right_margin=Inches(.72)
    sec.header_distance=Inches(.25);sec.footer_distance=Inches(.3)
    for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3']:
        style=doc.styles[name];style.font.name='Microsoft YaHei';style._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Microsoft YaHei');style.font.color.rgb=RGBColor(0,0,0)
        for border in list(style._element.iter(qn('w:pBdr'))):border.getparent().remove(border)
    normal=doc.styles['Normal'];normal.font.size=Pt(10.5);normal.paragraph_format.line_spacing=1.25;normal.paragraph_format.space_after=Pt(6)
    for name,size,before,after in [('Title',25,0,13),('Heading 1',17,21,11),('Heading 2',12,13,7),('Heading 3',11,11,6)]:
        s=doc.styles[name];s.font.size=Pt(size);s.font.bold=True;s.paragraph_format.space_before=Pt(before);s.paragraph_format.space_after=Pt(after);s.paragraph_format.keep_with_next=True
    doc.core_properties.title=source.stem
    doc.core_properties.subject='美食视频周报'
    doc.core_properties.author=''
    doc.core_properties.keywords='美食 视频 周报'
    header=sec.header.paragraphs[0];header.text='FOOD NOTES   /   美食视频周报';header.runs[0].font.size=Pt(8);header.runs[0].font.color.rgb=RGBColor.from_string('666D66')
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    r=footer.add_run((re.search(r'\d{4}-\d{4}-\d{4}',source.stem).group() if re.search(r'\d{4}-\d{4}-\d{4}',source.stem) else '')+'   ·   ');r.font.size=Pt(8)
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)

    def clean(s):
        return html.unescape(s.replace('\\|','|').replace('\\[','[').replace('\\]',']').replace('\\\\','\\'))
    def runs(p,s):
        pos=0
        for m in re.finditer(r'\[([^\]]+)\]\((https?://[^)]+)\)|\*\*([^*]+)\*\*',s):
            if m.start()>pos:p.add_run(clean(s[pos:m.start()]))
            if m.group(1) is not None:
                rid=p.part.relate_to(m.group(2),RELATIONSHIP_TYPE.HYPERLINK,is_external=True)
                link=OxmlElement('w:hyperlink');link.set(qn('r:id'),rid)
                run=OxmlElement('w:r');props=OxmlElement('w:rPr');color=OxmlElement('w:color');color.set(qn('w:val'),'315F8A');props.append(color)
                font=OxmlElement('w:rFonts');font.set(qn('w:eastAsia'),'Microsoft YaHei');font.set(qn('w:ascii'),'Microsoft YaHei');props.append(font)
                run.append(props);t=OxmlElement('w:t');t.text=clean(m.group(1));run.append(t);link.append(run);p._p.append(link)
            else:p.add_run(clean(m.group(3))).bold=True
            pos=m.end()
        if pos<len(s):p.add_run(clean(s[pos:]))
        return p
    def paragraph(s,style=None):return runs(doc.add_paragraph(style=style),s)
    def splitrow(line):return re.split(r'(?<!\\)\|',line.strip().strip('|'))

    lines=text.splitlines();i=0;section='';index_count=0
    while i<len(lines):
        line=lines[i].strip();i+=1
        if not line:continue
        if line.startswith('# '):
            paragraph(clean(line[2:]),'Title');continue
        if line.startswith('## '):
            section=line[3:5]
            if section in ('05','06'):
                new=doc.add_section(WD_SECTION_START.NEW_PAGE)
                new.orientation=WD_ORIENT.LANDSCAPE if section=='05' else WD_ORIENT.PORTRAIT
                new.page_width=Inches(11 if section=='05' else 8.5);new.page_height=Inches(8.5 if section=='05' else 11)
                new.left_margin=Inches(.55 if section=='05' else .72);new.right_margin=new.left_margin
            title=line[3:].replace('｜','  ');paragraph(title,'Heading 1');continue
        if line.startswith('### '):
            title=line[4:].replace('｜','  ');paragraph(title,'Heading 2');continue
        if line.startswith('|'):
            block=[line]
            while i<len(lines) and lines[i].strip().startswith('|'):block.append(lines[i].strip());i+=1
            table_rows=[[v.strip() for v in splitrow(s)] for s in block if not re.match(r'^\|\s*:?-+',s)]
            if section=='05':index_count=len(table_rows)-1
            groups=[[table_rows[0]]+table_rows[k:k+6] for k in range(1,len(table_rows),6)] if section=='05' else [table_rows]
            for group_index,table_rows in enumerate(groups):
                if group_index:doc.add_page_break()
                table=doc.add_table(rows=0,cols=len(table_rows[0]));table.alignment=WD_TABLE_ALIGNMENT.CENTER;table.autofit=False
                widths=[1.35,.65,5.06] if len(table_rows[0])==3 else [1.35,1.5,2.45,3.0,1.6]
                for n,row in enumerate(table_rows):
                    cells=table.add_row().cells
                    for j,value in enumerate(row):
                        cells[j].width=Inches(widths[j]);cells[j].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                        pr=cells[j]._tc.get_or_add_tcPr();shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E6EFF8' if n==0 else ('F6F8FA' if n%2==0 else 'FFFFFF'));pr.append(shade)
                        margins=OxmlElement('w:tcMar')
                        for side in ['top','left','bottom','right']:
                            m=OxmlElement('w:'+side);m.set(qn('w:w'),'70');m.set(qn('w:type'),'dxa');margins.append(m)
                        pr.append(margins);runs(cells[j].paragraphs[0],value)
                        for run in cells[j].paragraphs[0].runs:run.font.size=Pt(9.5);run.bold=n==0
                        for run_xml in cells[j]._tc.iter(qn('w:r')):
                            rp=run_xml.find(qn('w:rPr'))
                            if rp is None:rp=OxmlElement('w:rPr');run_xml.insert(0,rp)
                            sz=OxmlElement('w:sz');sz.set(qn('w:val'),'19');rp.append(sz)
                        cells[j].paragraphs[0].paragraph_format.space_after=Pt(1);cells[j].paragraphs[0].paragraph_format.line_spacing=1.15
                    trPr=table.rows[-1]._tr.get_or_add_trPr();cant=OxmlElement('w:cantSplit');trPr.append(cant)
                    if n==0:
                        repeat=OxmlElement('w:tblHeader');trPr.append(repeat)
                for j,width in enumerate(widths):table.columns[j].width=Inches(width)
                borders=OxmlElement('w:tblBorders')
                for edge in ['top','left','bottom','right','insideH','insideV']:
                    b=OxmlElement('w:'+edge);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'D9D9D9');borders.append(b)
                table._tbl.tblPr.append(borders)
            continue
        if line.startswith('> '):line=line[2:]
        if line.startswith('- '):paragraph(line[2:],'List Bullet')
        else:paragraph(line)

    assert index_count==sum(1 for line in lines if re.match(r"^\| \d{4}-.*-\d{3} \|",line))
    doc.save(dest)
    links=re.findall(r'\]\((https?://[^)]+)\)',text)


    return {'rows':index_count,'links':len(links)}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--format',choices=['docx','pdf','both'],default='docx')
    a=p.parse_args(argv)
    if not a.input.is_file():p.error('Markdown input not found')
    soffice=shutil.which('soffice') or shutil.which('soffice.exe')
    if a.format!='docx' and not soffice:p.error('Automatic PDF export needs LibreOffice. Use --format docx and save as PDF in Word, or install LibreOffice.')
    outputs=[a.output_dir/(a.input.stem+ext) for ext in (['.docx'] if a.format=='docx' else ['.pdf'] if a.format=='pdf' else ['.docx','.pdf'])]
    if any(f.exists() for f in outputs):p.error('Output exists; use another output directory to retain the old edition')
    a.output_dir.mkdir(parents=True,exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='food-report-export-') as temp:
            scratch=Path(temp);docx=scratch/(a.input.stem+'.docx')
            result=export_docx(a.input,docx)
            if a.format!='docx':
                profile=(scratch/'profile').resolve().as_uri()
                flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
                subprocess.run([soffice,'-env:UserInstallation='+profile,'--headless','--convert-to','pdf','--outdir',str(scratch),str(docx)],check=True,capture_output=True,timeout=120,creationflags=flags)
                if not docx.with_suffix('.pdf').is_file():raise RuntimeError('PDF renderer did not produce a file')
            for target in outputs:shutil.copyfile(docx.with_suffix(target.suffix),target)
        print(json.dumps({'outputs':[str(f) for f in outputs],**result,'visual_review_required':True},ensure_ascii=False))
    except ImportError as error:p.error('Word export needs optional dependencies: python -m pip install -e ".[export]". '+str(error))
