# Stage 8 — реєстр OPEN-вимог (не заявляти без доказів)

Ці пункти **свідомо залишені поза MVP** Stage 8. Скрипт `scripts/open_requirements_register.py` (або `demo_from_zero`) записує **`reports/open_requirements_register.json`** — каталог `reports/` у `.gitignore`, у репо лише зразок: `examples/stage8_open_requirements_register.example.json`.

## Semantic graph {#semantic-graph}

**Статус:** OPEN  
**Зараз:** лексичний GraphRAG-lite (`extract_entities`, MENTIONS у Neo4j).  
**Щоб закрити:** типізовані відношення, валідація на розміченому корпусі, метрики precision/recall по triples.

## Multimodal {#multimodal}

**Статус:** OPEN  
**Зараз:** Tesseract OCR для текстового шару скану; текстові PDF через pypdf.  
**Не входить:** креслення, складні таблиці, VLM.  
**Щоб закрити:** окремий pipeline + eval на анотованих зображеннях/таблицях.

## Air-gap audit {#air-gap}

**Статус:** OPEN  
**Зараз:** `compose.yaml` з `internal: true` для лабораторії; `compose.dev.yaml` — лише локальний доступ до API.  
**Не є доказом:** відсутність egress на рівні хоста, перевірка образів, DNS leak test, pen-test.  
**Щоб закрити:** операторський чекліст (iptables/cloud FW), журнал pull образів, незалежний security review.

## GPU benchmark {#gpu-benchmark}

**Статус:** OPEN  
**Зараз:** `scripts/load_test.py` — клієнтські HTTP latency/RPS; не tokens/s.  
**Щоб закрити:** вимірювання на Ollama з `nvidia-smi` / вбудованими метриками, фіксація SKU GPU, TTFT і tokens/s для `bge-m3` та `qwen2.5:3b`.

---

**Портфоліо:** live-докази Stage 8 покривають синтетичний Docker E2E, OCR smoke, RAG eval із faithfulness-полями та client load. OPEN-пункти вище — дорожня карта, не приховування.