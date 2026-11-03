export PATH="$HOME/.local/bin:$PATH"
source ~/venv/py310/bin/activate
uv pip install pymupdf 2>&1 | tail -1
cat > /root/readpdf.py <<'PY'
import fitz
d = fitz.open('/root/sample.pdf')
print(len(d), 'pages')
for i, p in enumerate(d):
    print('--- p%d ---' % (i + 1))
    print(p.get_text())
    p.get_pixmap(dpi=70).save('/root/s%d.png' % (i + 1))
PY
python /root/readpdf.py
