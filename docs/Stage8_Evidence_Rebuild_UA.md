# Перезбірка ZIP-доказів під актуальний коміт

## Проблема
Реліз `stage8-submission-2026-11-17` містить ZIP, зібраний **до** змін eval/preflight (`96cfae3` і новіші). Код на GitHub і архів на Releases можуть **розходитися** — це неприпустимо для OTUS.

## Один ланцюг (рекомендовано)
```powershell
# 1. Чистий стенд за потреби: docker compose down -v
powershell -ExecutionPolicy Bypass -File scripts\demo_from_zero.ps1
# Має завершитися без throw; у reports/stage8_preflight.json → mvp_acceptance: PASS

# 2. ZIP (без -AllowStaleEvidence)
powershell -ExecutionPolicy Bypass -File scripts\bundle_stage8_evidence.ps1

# 3. Перевірити manifest у ZIP
# reports/stage8_live_evidence_manifest.json → git_commit == git rev-parse HEAD

# 4. Оновити GitHub Release (новий тег або upload поверх)
$tag = 'stage8-submission-2026-11-17'   # або новий: stage8-evidence-YYYY-MM-DD
git rev-parse --short HEAD
gh release upload $tag reports\EAKP_Stage8_Live_Evidence_*.zip --clobber
gh release upload $tag presentation\EAKP_OTUS_Defense_Stage8_UA.pptx --clobber
```

`scripts/verify_mvp_evidence.py` повинен повернути **0** перед bundle (MVP-артефакти + `git_commit` у preflight **дорівнює** `git rev-parse HEAD`).

Перший `stage8_preflight.py --require-mvp-live` на чистому `reports/` не вимагає попереднього preflight-файлу — лише smoke/OCR/RAG/load JSON.

## Статуси
| Поле | Очікування для MVP |
|---|---|
| `mvp_acceptance` | `PASS` |
| `release_acceptance` | `BLOCKED` (OPEN: semantic, multimodal, air-gap, GPU) |
| `eval_schema_version` у RAG JSON | `>= 2` |
| `git_commit` у preflight/manifest | = `HEAD` після прогону |

## Якщо Docker зараз недоступний
Не оновлюйте ZIP на Release. У листі до викладача вкажіть **коміт коду** і що архів буде перезібраний після live-прогону (`demo_from_zero`).