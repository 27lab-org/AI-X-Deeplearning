import fitz
d = fitz.open('/root/sample.pdf')
print(len(d), 'pages')
for i, p in enumerate(d):
    print('--- p%d ---' % (i + 1))
    print(p.get_text())
    p.get_pixmap(dpi=70).save('/root/s%d.png' % (i + 1))
