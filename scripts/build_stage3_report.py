from pathlib import Path
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, KeepTogether)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import mm

root = Path(__file__).resolve().parents[1]
out = Path('/mnt/data/EAKP_Stage3_Backend_Report_UA.pdf')
pdfmetrics.registerFont(TTFont('Noto', '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'))
pdfmetrics.registerFont(TTFont('NotoBold', '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf'))
navy = colors.HexColor('#16334F')
blue = colors.HexColor('#1763A3')
green = colors.HexColor('#087b60')
gray = colors.HexColor('#526477')
styles={
 'cover': ParagraphStyle('cover',fontName='NotoBold',fontSize=23,leading=29,textColor=navy,spaceAfter=20),
 'subtitle': ParagraphStyle('subtitle',fontName='Noto',fontSize=13,leading=19,textColor=blue,spaceAfter=15),
 'h1': ParagraphStyle('h1',fontName='NotoBold',fontSize=15,leading=19,textColor=navy,spaceBefore=19,spaceAfter=8),
 'h2': ParagraphStyle('h2',fontName='NotoBold',fontSize=11.4,leading=15,textColor=blue,spaceBefore=11,spaceAfter=5),
 'body': ParagraphStyle('body',fontName='Noto',fontSize=9.5,leading=14.1,textColor=navy,spaceAfter=8),
 'small': ParagraphStyle('small',fontName='Noto',fontSize=8.3,leading=12,textColor=gray,spaceAfter=6),
 'cell': ParagraphStyle('cell',fontName='Noto',fontSize=8.3,leading=11.5,textColor=navy),
 'cellb': ParagraphStyle('cellb',fontName='NotoBold',fontSize=8.2,leading=11.3,textColor=navy),
 'white': ParagraphStyle('white',fontName='NotoBold',fontSize=8.5,leading=12,textColor=colors.white),
}
body=[]
def para(s, style='body'): body.append(Paragraph(s, styles[style]))
def head(s): para(s,'h1')
def row(vals, widths, header=True):
    rows=[]
    for i,line in enumerate(vals):
        st='white' if header and i==0 else 'cell'
        rows.append([Paragraph(str(x),styles[st]) for x in line])
    t=Table(rows,colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT')
    ts=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('LINEBELOW',(0,0),(-1,-1),0.35,colors.HexColor('#d8e2ec'))]
    if header: ts.append(('BACKGROUND',(0,0),(-1,0),blue))
    for i in range(1,len(rows)):
        if i%2==0: ts.append(('BACKGROUND',(0,i),(-1,i),colors.HexColor('#f0f5fa')))
    t.setStyle(TableStyle(ts)); body.append(t)

para('Enterprise AI<br/>Knowledge Platform','cover')
para('Етап №3 — реалізація Python/FastAPI Backend','subtitle')
para('<b>OTUS Architect AI/ML</b> | 16 листопада 2026 | Версія v0.3')
para('<b>Підсумок:</b> реалізовано запускний бекенд із локальною автентифікацією, базою даних, правами доступу, завантаженням PDF та фоновим вилученням тексту. AI-модель і GraphRAG — наступний етап.')
row([['Показник','Підтверджений стан'],['Автотести','8 із 8 пройдено на локальній SQLite'],['Міграції','Alembic upgrade head пройдено на SQLite'],['Docker Compose + PostgreSQL','Файли створено, але Docker тут не запущено'],['LLM / GraphRAG','Ще не реалізовано, endpoint /query повертає 501']], [60*mm,106*mm])
head('1. Реалізовані функції')
for x in [
 'Авторизація: Argon2-хешування паролів, короткоживучі JWT, перевірка підпису, issuer та audience.',
 'Адміністрування: локальне створення облікових записів і груп, управління членством.',
 'Документи: PDF upload із лімітом 12 MB, MIME/header check, SHA256 та приватним сховищем.',
 'Доступ: document-level ACL для user/group, default deny, 404 для чужого документа, revoke та acl_epoch.',
 'Черга: ingestion_jobs у PostgreSQL/SQLite, базові lease/retry та окремий worker.',
 'PDF: локальне витягування тексту з номерами сторінок; відсутність текстового шару позначається NEEDS_OCR.',
]: para('• '+x)
para('Важливо: TEXT_EXTRACTED — це не READY. Поле active_index_run_id лишається NULL, індекси Qdrant/Neo4j поки не існують.','small')
body.append(PageBreak())
head('2. C4 Level 4 — фактична структура модулів')
img=Image(str(root/'diagrams'/'c4_level4_code.png'))
img_width, img_height = img.imageWidth, img.imageHeight
img.drawWidth=163*mm
img.drawHeight=img_height*img.drawWidth/img_width
body.append(img)
para('У Stage 3 контролер FastAPI, auth/policy та SQLAlchemy реалізовані окремими Python-модулями. Локальне файлове сховище — тимчасовий адаптер до майбутнього приватного S3/MinIO.', 'small')
head('3. Основні HTTP-ендпоїнти')
row([['Endpoint','Виконання'],
    ['POST /api/v1/auth/token','JWT login (пароль не зберігається відкритим текстом)'],
    ['GET /api/v1/auth/me','Профіль поточного користувача'],
    ['POST /api/v1/documents','Прийом PDF, створення immutable version і ingestion job'],
    ['GET /api/v1/documents/{id}','Метадані лише за ACL'],
    ['GET /api/v1/documents/{id}/download','Повернення PDF лише за ACL'],
    ['POST /api/v1/documents/{id}/acl','Видача/відкликання доступу; збільшення epoch'],
    ['GET /api/v1/jobs/{id}','Технічний стан завдання за write-ACL'],
    ['POST /api/v1/query','HTTP 501 до впровадження GraphRAG']], [74*mm,92*mm])
body.append(PageBreak())
head('4. Виконані перевірки')
row([['Категорія','Перевірка'],
    ['Ідентифікація','401 без JWT та з підробленим JWT; невірний пароль'],
    ['Isolation','Bob не бачить та не завантажує PDF Alice; jobs не видимі'],
    ['ACL','Grant/revoke user і group; epoch під час зміни груп'],
    ['Spoofing','role/user_id у JSON не змінює principal'],
    ['Upload','Відхилено некоректний PDF та завеликий файл'],
    ['Worker','Витяг тексту з page_number та scanned PDF → NEEDS_OCR'],
    ['DB migration','Alembic upgrade створює реальні таблиці'],
    ['Query','Не повертає вигаданих відповідей: 501']], [50*mm,116*mm])
head('5. Відомі обмеження безпеки')
for x in [
 'Немає HTTPS reverse proxy, зовнішнього OIDC/SSO, rate limiting, антивірусної перевірки та повного session revocation.',
 'Не перевірено заборону outbound internet на рівні host firewall; внутрішня Docker network сама по собі не гарантує air-gap.',
 'Не перевірено Docker/PostgreSQL runtime, конкуренцію кількох воркерів, p95, RPS або VRAM.',
 'Відкликання ACL не гарантує відкликання байтів, передавання яких вже почалося по HTTP.',
]: para('• '+x)
head('6. Як почати')
para('Завантажте ZIP-пакет із вихідним кодом. У корені є <b>README.md</b>, <b>compose.yaml</b>, <b>Dockerfile</b> та <b>.env.example</b>. Згенеруйте два різні секрети, виконайте Docker Compose, створіть першого admin-користувача через CLI та перевірте /readyz.')
para('Для локального запуску без Docker використовуйте SQLite й команди з README. Перевірка: <b>pytest -q</b>.','small')
body.append(PageBreak())
head('7. Що робимо в етапі №4')
row([['Компонент','План'],
    ['Offline OCR','Локальна модель для сканованих PDF, цитування сторінок'],
    ['Vector index','Qdrant з chunk provenance, index_run_id'],
    ['Knowledge graph','Neo4j document-scoped entities + edges з provenance'],
    ['Index publication','Staging → verify → atomic PostgreSQL active_index_run_id'],
    ['Local LLM','Serving engine за результатами hardware sizing'],
    ['Orchestration','LangGraph зі scoped retrieval та citation/epoch gate'],
    ['Negative security tests','Індекси/graph traversal не можуть розкрити секрет User B']], [50*mm,116*mm])
head('8. Стан усього проєкту')
row([['Етап','Статус'], ['1. PRD/SRS/C4 L1–2','✓ Готово'], ['2. C4 L3/Deployment/Sequence/ER/DFD','✓ Готово'],
     ['3. FastAPI/PostgreSQL/ACL/Uploads/Worker','✓ Код, 8 локальних тестів'],
     ['4. GraphRAG/LLM/LangGraph','Попереду'], ['5. Security hardening','Попереду'],
     ['6. Observability + load tests','Попереду'], ['7. Final demo / defense','Попереду']],[104*mm,62*mm])
para('Перші три етапи не означають виконання всіх вимог OTUS: критерій GraphRAG та безпека end-to-end залишаються відкритими.','small')

def canvas_footer(canvas, doc):
    canvas.saveState()
    W,H=A4
    canvas.setStrokeColor(colors.HexColor('#c4d4e2'))
    canvas.line(19*mm,18*mm,W-19*mm,18*mm)
    canvas.setFont('Noto',8)
    canvas.setFillColor(gray)
    canvas.drawString(19*mm,12*mm,'EAKP • OTUS Architect AI/ML • Stage 3')
    canvas.drawRightString(W-19*mm,12*mm,f'{doc.page}')
    canvas.restoreState()

doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=19*mm,leftMargin=19*mm,
                      topMargin=19*mm,bottomMargin=24*mm,title='EAKP Stage 3 — Backend Report (UA)',
                      author='EAKP technical design package')
doc.build(body,onFirstPage=canvas_footer,onLaterPages=canvas_footer)
print(out)
