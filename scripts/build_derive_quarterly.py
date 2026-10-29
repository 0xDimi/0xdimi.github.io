"""Add a portfolio cover to the complete signed-in Alea report export."""
import hashlib
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'source-pdfs/derive-q3-2026-source.pdf'
OUTPUT = ROOT / 'docs/pdfs/derive-q3-2026.pdf'
URL = 'https://alearesearch.io/reports/benchmark/derive-q3-2026'
SHA256 = 'bd6a7a025137a1bec19271af512566f6d347000bbde41e25d74d38f1ca507020'


def main():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Source export changed; review before rebuilding')
    with fitz.open(SOURCE) as original:
        if len(original) != 23 or 'Disclosures' not in original[21].get_text():
            raise ValueError('Unexpected source export or missing disclosures')
        with fitz.open() as out:
            page = out.new_page(width=original[0].rect.width, height=original[0].rect.height)
            dark, gold, cream, muted = (0.063,0.173,0.204), (0.84,0.69,0.46), (0.965,0.957,0.929), (0.73,0.82,0.83)
            w, h = page.rect.width, page.rect.height
            page.draw_rect(page.rect, color=dark, fill=dark)
            page.draw_rect(fitz.Rect(45,45,85,85), color=gold, width=.8)
            page.insert_text((53,72),'DP',fontname='tiro',fontsize=19,color=gold)
            page.insert_text((105,68),'SELECTED RESEARCH / QUARTERLY REPORT',fontname='helv',fontsize=8,color=muted)
            page.insert_text((45,220),'DIMITRIS PECHLIVANIDIS',fontname='helv',fontsize=10,color=gold)
            page.insert_text((45,290),'Derive',fontname='tiro',fontsize=58,color=cream)
            page.insert_text((45,340),'Q3 2026 Benchmark',fontname='tiro',fontsize=35,color=cream)
            page.draw_line((45,380),(170,380),color=gold)
            page.insert_text((45,410),'Work for Alea Research',fontname='helv',fontsize=12,color=cream)
            page.insert_text((45,434),'Published October 28, 2026',fontname='helv',fontsize=10,color=muted)
            page.draw_line((45,h-105),(w-45,h-105),color=muted,width=.5)
            page.insert_text((45,h-78),'Portfolio edition. Original report and disclosures follow.',fontname='helv',fontsize=9,color=muted)
            page.insert_text((45,h-57),'Read the original publication',fontname='helv',fontsize=9,color=gold)
            page.insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(45,h-70,200,h-45),'uri':URL})
            out.insert_pdf(original,from_page=0,to_page=21,links=True,annots=True)
            out.set_metadata({'title':'Derive: Q3 2026 - Portfolio edition','author':'Dimitris Pechlivanidis','subject':'Work for Alea Research'})
            out.save(OUTPUT,garbage=4,deflate=True)
    with fitz.open(OUTPUT) as result:
        assert len(result)==23 and 'Disclosures' in result[-1].get_text()
        assert sum(len(p.get_images()) for p in result)>=28
        assert sum(len(p.get_links()) for p in result)>50
    print(f'Built {OUTPUT}: 23 pages')

if __name__ == '__main__':
    main()
