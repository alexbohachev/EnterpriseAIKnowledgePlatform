# Набори для RAG evaluation

| Файл | Призначення |
|---|---|
| `eval_template.jsonl` | Шаблон з `REPLACE_*` — не запускати без заміни |
| `eval_live_synthetic.jsonl` | 2 кейси з фіксованими UUID (історичний live-стенд) |
| `eval_live_bob_acl.jsonl` | 1 кейс ізоляції Bob |
| `reports/eval_active_*.jsonl` | Генерується `scripts/seed_synthetic_eval_corpus.py` (8 Alice + 4 Bob) |

Поля кейсу (розширено **faithfulness**):

- `must_include` — фрагменти, що мають з’явитися у відповіді
- `must_not_include` — заборонені галюцинації / плутанина дат
- `require_citation_marks` — у відповіді має бути `[S1]` тощо, якщо є цитати
- `min_citations` / `require_citations_when_answered` — мінімум цитат у JSON
- `abstain_mode`: `acl_denied` (ізоляція доступу, `forbidden_doc_ids`) або `unanswerable` (тема поза корпусом; retrieval дозволений)
- `expected_abstain` — застарілий прапорець; краще явний `abstain_mode`

Звіт: `quality_pass_rate`, `faithfulness_pass_rate` у `reports/rag_eval*.json`.