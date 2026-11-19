# Teleprompter — Stage 8 defense (9 slides)

## Слайд 1: Slide 1

ФІНАЛЬНИЙ ПРОЄКТ / MVP

Enterprise AI Knowledge Platform

EAKP · OTUS AI/ML Architect · MVP Candidate

1

Захищений пошук корпоративних знань
із GraphRAG та контрольованими цитатами

Stage 8 · MVP (live-докази)

49 passed pytest (3 skip)  •  mvp_acceptance: PASS  •  query p95 — клієнтський, не GPU


## Слайд 2: Slide 2

ЦІННІСТЬ

Бізнес-проблема та MVP

EAKP · OTUS AI/ML Architect · MVP Candidate

2

Корпоративні знання розкидані між PDF та системами.

LLM без ACL і provenance може видати чужий контекст.

Мета: локальний пошук із джерелами та відкликанням доступу.

Синтетичне демо без секретів


## Слайд 3: Slide 3

C4 / DEPLOYMENT

Системний дизайн: control & data planes

EAKP · OTUS AI/ML Architect · MVP Candidate

3

CONTROL PLANE

API · ACL · LangGraph
SQL publication pointer

DATA PLANE

PostgreSQL · Qdrant
Neo4j · Ollama


## Слайд 4: Slide 4

PIPELINE

Потік: документ → відповідь

EAKP · OTUS AI/ML Architect · MVP Candidate

4

PDF

Text only

→

Chunks

Provenance

→

Index

Qdrant+Neo4j

→

ACL

SQL gate

→

LLM

Local answer

Зовнішні індекси не мають права вирішувати доступ.

Після LLM — повторна перевірка SQL ACL та версії індексу.


## Слайд 5: Slide 5

АРХІТЕКТУРНІ РІШЕННЯ

Стек і ключові компроміси

EAKP · OTUS AI/ML Architect · MVP Candidate

5

FastAPI + PostgreSQL

API / права і публікація індексу

Qdrant + Neo4j

Recall + графові зв’язки; дві бази

LangGraph + Ollama

Локальна оркестрація та інференс

Prometheus / OTLP

Метрики і трасування; live proof OPEN


## Слайд 6: Slide 6

VERIFICATION

Які результати реально підтверджені

EAKP · OTUS AI/ML Architect · MVP Candidate

6

49 passed (+3 skip)

Модульні та API-тести (SQLite/fakes + OCR skip на хості)

PASS (synthetic)

Live Docker E2E + OCR + RAG eval 8+4

mvp_acceptance: PASS у ZIP; release_acceptance: BLOCKED (OPEN scope).


## Слайд 7: Slide 7

READINESS GAP

Обмеження, які ми НЕ приховуємо

EAKP · OTUS AI/ML Architect · MVP Candidate

7

OCR — лише текст зі скану (Tesseract); креслення/VLM і складні таблиці — OPEN.

GraphRAG-lite: лексичні сутності, без типізованого semantic KG.

Немає formal GPU tokens/s, air-gap audit і pen-test; load_query — клієнтський HTTP.

Guardrails — евристичні; penetration test не проводили.

NO-GO до закриття acceptance gates


## Слайд 8: Slide 8

ROADMAP

Докази приймання та наступні дії

EAKP · OTUS AI/ML Architect · MVP Candidate

8

G1–G2: закрито на синтетиці (smoke + ACL + OCR live).

G3–G4: Grafana/Jaeger + RAG eval v2 (faithfulness); людський red team — OPEN.

G5–G6: GPU inference bench, air-gap/red team, semantic KG / multimodal.

Цінність: керована довіра до знань, а не «LLM відповідає на все».


## Слайд 9: Stage 8: live-докази (синтетичний стенд)

• Docker E2E + integration_probe: overall_ok
• integration_smoke + OCR live E2E (синтетичні PDF)
• RAG eval v2: quality 1.0, faithfulness 1.0; Bob ACL 4/4
• Query load (клієнт): p95 у межі gate — не GPU tokens/s
• Monitoring: Grafana / Prometheus / Jaeger
• release_acceptance: BLOCKED (air-gap, GPU, pen-test)

