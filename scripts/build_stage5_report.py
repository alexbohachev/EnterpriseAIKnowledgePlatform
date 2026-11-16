"""Build Ukrainian A4 print report for Stage5, using ReportLab and DejaVu fonts."""
from pathlib import Path
from xml.sax.saxutils import escape
import fitz
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, Image, KeepTogether
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

root=Path(__file__).resolve().parents[1]
out=Path('/mnt/data/EAKP_Stage5_Security_Report_UA.pdf')
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
fontb='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
for path in (font,fontb): assert Path(path).is_file()
pdfmetrics.registerFont(TTFont('DejaVu',font))
pdfmetrics.registerFont(TTFont('DejaVuBold',fontb))
pdfmetrics.registerFontFamily('DejaVu', normal='DejaVu', bold='DejaVuBold')
navy=HexColor('#153D61'); blue=HexColor('#1D75A5'); pale=HexColor('#EAF2F8'); grey=HexColor('#405365'); green=HexColor('#19714D'); amber=HexColor('#AB6A16')
styles={
'title':ParagraphStyle('title',fontName='DejaVuBold',fontSize=20,leading=25,textColor=navy,spaceAfter=12),
'sub':ParagraphStyle('sub',fontName='DejaVu',fontSize=11,leading=16,textColor=grey,spaceAfter=16),
'h1':ParagraphStyle('h1',fontName='DejaVuBold',fontSize=14,leading=19,textColor=navy,spaceBefore=16,spaceAfter=9),
'h2':ParagraphStyle('h2',fontName='DejaVuBold',fontSize=10.5,leading=15,textColor=blue,spaceBefore=10,spaceAfter=6),
'body':ParagraphStyle('body',fontName='DejaVu',fontSize=9.5,leading=15,textColor=grey,spaceAfter=7),
'compact':ParagraphStyle('compact',fontName='DejaVu',fontSize=8.35,leading=12,textColor=grey,spaceAfter=4),
'caption':ParagraphStyle('caption',fontName='DejaVu',fontSize=8.2,leading=12,textColor=grey,spaceBefore=4,spaceAfter=7),
'headcell':ParagraphStyle('headcell',fontName='DejaVuBold',fontSize=8,leading=11,textColor=HexColor('#FFFFFF')),
'cell':ParagraphStyle('cell',fontName='DejaVu',fontSize=8.0,leading=11,textColor=grey),
}

def p(text,style='body'):
    return Paragraph(text,styles[style])
def bullet(text):
    return p('• '+text,'body')
def table(rows,widths,header=True):
    r=[]
    for i,row in enumerate(rows): r.append([p(escape(str(v)), 'headcell' if i==0 and header else 'cell') for v in row])
    t=Table(r,colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT')
    cmds=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('GRID',(0,0),(-1,-1),0.35,HexColor('#D8E3EA'))]
    if header:cmds+=[('BACKGROUND',(0,0),(-1,0),navy),('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#F6FAFC'),HexColor('#FFFFFF')])]
    t.setStyle(TableStyle(cmds));return t

body=[]
body.extend([Spacer(1,9*mm),p('ENTERPRISE AI KNOWLEDGE PLATFORM','title'), p('STAGE 5 · Security Hardening', 'sub'),
 p('<b>Звіт про реалізацію захисних контролів</b> · OTUS Architect AI/ML · Українська технічна редакція'),
 p('<b>Статус:</b> код оновлено, локальні автоматизовані тести пройдено. Це не аудит безпеки, не підтвердження air-gap і не сертифікація Production.'),
 p('Реалізована робота базується на Stage 4 (GraphRAG-lite з SQL ACL) та письмовому завданні на закриту корпоративну AI-платформу.'),
 p('Підсумок контролів','h1'),
 table([('Контроль','Виконано в Stage 5','Зауваження'),
 ('JWT / logout','token_version, invalidate all tokens','Потрібна PostgreSQL-міграція'),
 ('Обмеження запитів','429 login/query/upload','Лише одна API-репліка'),
 ('Prompt injection','Евристичні input/context guards','Не гарантована стійкість'),
 ('PII','Regex-маскування запитів, контексту, відповіді','Не охоплює всі формати'),
 ('Відповіді LLM','Перевірка посилань [S1]…[Sn]','Цитата ≠ доказ істинності'),
 ('Egress hardening','Allowlist endpoint, proxy bypass','Потрібен firewall'),
 ('HTTP / контейнер','Security headers, read-only FS, drops caps','Compose не запускався')],[34*mm,65*mm,77*mm]),
 Spacer(1,4*mm),p('Результат перевірок: <b>28/28 тестів успішні</b>. Частина застосовує FakeChat/FakeVectors/FakeGraph та SQLite. Реальні Neo4j, Qdrant, Ollama, GPU й Docker Compose не перевірялися.'),
 PageBreak(), p('Архітектура: межі довіри','h1')])
img=Image(str(root/'diagrams/stage5_security.png')); ow,oh=img.imageWidth,img.imageHeight; target=175*mm; img.drawWidth=target;img.drawHeight=target*oh/ow;body.append(img)
body.append(p('Дані в індексах недовірені. PostgreSQL — єдина точка істини для прав і версії активного індексу. Локальна модель отримує маскований контекст, але евристики не замінюють політики безпеки.','caption'))
body.extend([p('Ланцюг запиту','h2'),
 bullet('<b>1.</b> FastAPI перевіряє JWT та ліміт користувача, відхиляє деякі відомі атаки в питанні.'),
 bullet('<b>2.</b> SQL визначає перелік дозволених та опублікованих документів.'),
 bullet('<b>3.</b> Qdrant і Neo4j повертають лише кандидатні ідентифікатори; SQL і ACL повторно перевіряють фрагменти.'),
 bullet('<b>4.</b> Перед локальною LLM частина директив у PDF приховується, PII маскується; кількість символів контексту обмежена.'),
 bullet('<b>5.</b> Результат валідується за source IDs, застосовується маскування PII, а ACL та token_version ще раз перевіряються.'),
 p('Маршрути Stage 5','h2'),
 table([('Метод','Endpoint','Призначення'),('POST','/api/v1/auth/logout-all','Відкликає всі JWT поточного користувача'),('POST','/api/v1/users/{id}/revoke-tokens','Адміністратор відкликає JWT користувача')],[24*mm,82*mm,70*mm]),
 PageBreak(),p('Що саме перевірено','h1'),
 p('Локальний тестовий набір запускали проти вихідного коду Stage 5. Для API використовувався FastAPI TestClient; для БД — SQLite; для RAG — тестові адаптери. Це підтверджує логіку коду в ізоляції, а не безпеку інфраструктури.'),
 table([('Пакет','К-сть','Покриті перевірки'),('Stage 3 — API/міграції/PDF','8','JWT, ACL, групи, права доступу, upload validation, Alembic, worker'),('Stage 4 — RAG','6','Подвійна публікація, компенсація, SQL ACL, сусіди графа, revoke-in-flight'),('Stage 5 — security','14','token revoke, rate limit, guards, PII, citations, конфігурація, headers, host'),('Разом','28','28 пройдених тестів')],[57*mm,21*mm,98*mm]),
 Spacer(1,5*mm),p('Покриття модельних загроз','h2'),
 bullet('Тест викрадення інформації іншим користувачем: без SQL-доступу відповідні фрагменти не передаються FakeChat.'),
 bullet('Тест відкликання токена та прав під час генерації: відповідь відкидається до відправлення.'),
 bullet('Тест prompt injection: очевидна директива у питанні повертає 422; директива в PDF приховується.'),
 bullet('Тест PII: базові шаблони email/телефону/IBAN маскуються, вихідні дані не реекспонуються у відповіді.'),
 bullet('Тест некоректної відповіді: відсутні/помилкові source tags викликають fail-closed помилку.'),
 p('Додаткові перевірки збірки','h2'),
 bullet('Python: синтаксична компіляція застосунку та тестів завершилась без помилок.'),
 bullet('Alembic: міграція <b>0002_stage5</b> перевірена на SQLite й додає token_version.'),
 bullet('Wheel: у збірці присутні пакети <b>app</b> і <b>app.rag</b>; перевірено потрібні модулі.'),
 PageBreak(),p('Відомі ризики та наступні роботи','h1'),
 table([('Ризик','Що залишилося'),
 ('Немає повноцінного air-gap','Перевірити iptables / cloud firewall, DNS, Docker daemon, образи, модельний cache.'),
 ('Немає зовнішнього gateway','Додати TLS reverse proxy, shared rate limiting (Redis), WAF, request-size/time budgets.'),
 ('Слабкі regex guardrails','Побудувати adversarial prompt dataset, спеціалізований PII detector, обмеження інструментів.'),
 ('Секрети в ENV','Vault або захищені secrets files; ротація ключів, резервні процедури.'),
 ('Немає ізоляції PDF парсера','Обмеження CPU/RAM, sandbox, перевірка на шкідливі вкладення.'),
 ('Немає реального E2E тесту','Запустити PostgreSQL, Qdrant, Neo4j, Ollama, LangGraph на кінцевому хості.'),
 ('GraphRAG-lite, не semantic GraphRAG','Перевірити якість пошуку та точність відповідей проти baseline.'),
 ('Дані на локальному диску','Шифрування at rest, резервні копії, RPO/RTO, контроль адміністративного доступу.')],[62*mm,114*mm]),
 Spacer(1,5*mm),p('Критерії переходу до Stage 6','h2'),
 bullet('Є можливість запуску <b>docker compose</b> у контрольованому середовищі.'),
 bullet('Проведена інтеграційна перевірка ACL — користувач B не може прочитати дані A через жодний маршрут.'),
 bullet('Перевірені аварійні сценарії: модель недоступна, відмова graph/vector index, відкликання доступу.'),
 bullet('Виміряні RPS, p50/p95/p99 latency, error rate; результати наведені з апаратною конфігурацією.'),
 bullet('Оцінені faithfulness, groundedness, false-positive і false-negative rate guardrails.'),
 Spacer(1,6*mm),p('<b>Висновок.</b> Етап №5 завершено на рівні вихідного коду, unit/API тестування та документації. Повноцінну безпеку чи готовність до Production не доведено. Наступний етап — Observability, справжня інтеграція та вимірювання навантаження.'),
])

def add_footer(canvas: Canvas, doc):
 canvas.saveState()
 w,h=A4
 canvas.setStrokeColor(HexColor('#D6E4ED')); canvas.line(17*mm,18*mm,w-17*mm,18*mm)
 canvas.setFont('DejaVu',8)
 canvas.setFillColor(grey)
 canvas.drawString(17*mm,12.4*mm,'EAKP · Stage 5 · 16.11.2026 · Internal study report')
 canvas.drawRightString(w-17*mm,12.4*mm,f'{doc.page}')
 canvas.restoreState()

doc=SimpleDocTemplate(str(out), pagesize=A4,leftMargin=17*mm,rightMargin=17*mm,topMargin=16*mm,bottomMargin=22*mm,title='EAKP Stage 5 — Security Hardening',author='EAKP project')
doc.build(body,onFirstPage=add_footer,onLaterPages=add_footer)
pd=fitz.open(out)
print('PAGES',len(pd),'SIZE',out.stat().st_size)
for i,page in enumerate(pd):
 text=page.get_text()
 print(i+1,'chars',len(text),'rect',page.rect)
 assert page.rect.width > 595 and page.rect.height > 841
 assert len(text) > 250
 for b in page.get_text('blocks'):
  if b[6]==0:
   assert b[0]>=15 and b[2] <= page.rect.width-15 and b[1]>=12 and b[3] <= page.rect.height-7,(i,b)
print('output',out)
