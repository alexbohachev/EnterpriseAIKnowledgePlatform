# Teleprompter — Stage 8 defense (9 slides)

## Слайд 1: Slide 1

ФІНАЛЬНИЙ ПРОЄКТ / MVP

Enterprise AI Knowledge Platform

EAKP · OTUS AI/ML Architect · MVP Candidate

1

Захищений пошук корпоративних знань
із GraphRAG та контрольованими цитатами

Stage 7 · кандидат

37/37 локальних тестів  •  live Docker E2E — відкрито  •  RAG p95 — не виміряно


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

37 / 37

Модульні та API-тести

OPEN

Docker/LLM E2E

/healthz: 12/12 — це лише tiny HTTP diagnostic, не GraphRAG benchmark.


## Слайд 7: Slide 7

READINESS GAP

Обмеження, які ми НЕ приховуємо

EAKP · OTUS AI/ML Architect · MVP Candidate

7

Немає OCR, аналізу креслень або складних таблиць.

GraphRAG-lite: лексичні сутності, без типізованих відношень.

Немає реального p95/RPS, GPU sizing і доведеного air-gap.

Guardrails — евристичні; penetration test не проводили.

NO-GO до закриття acceptance gates


## Слайд 8: Slide 8

ROADMAP

Докази приймання та наступні дії

EAKP · OTUS AI/ML Architect · MVP Candidate

8

G1–G2: Docker E2E та ACL A/B/revoke на живих сервісах.

G3–G4: Grafana/Jaeger + реальна RAG-eval і людська фактперевірка.

G5–G6: LLM query benchmark, air-gap/red team, OCR/GraphRAG scope.

Цінність: керована довіра до знань, а не «LLM відповідає на все».


## Слайд 9: Stage 8: live-докази (синтетичний стенд)

• Docker E2E + integration_probe: overall_ok
• integration_smoke + OCR live E2E (синтетичні PDF)
• RAG eval: recall 1.0; Bob ACL abstention 1.0
• Query load (клієнт): p50 ~2.7s, p95 ~11.5s — не GPU
• Monitoring: Grafana / Prometheus / Jaeger
• release_acceptance: BLOCKED (air-gap, GPU, pen-test)

