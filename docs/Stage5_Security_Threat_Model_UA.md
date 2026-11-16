# Stage 5 — Security-by-Design: модель загроз і межі контролів

**Система:** Enterprise AI Knowledge Platform (EAKP), OTUS Architect AI/ML. **Статус:** MVP-прототип, локальні модульні тести, без формального аудиту або реального інтеграційного запуску.

## Джерело вимог та межі
Письмове завдання `project .txt` вимагає on-premise / air-gapped виконання, закриті локальні LLM, SQL-based ACL на фрагментах/вузлах графа, захист від prompt injection і PII та збереження поділу Control Plane / Data Plane. Наші Stage 5 рішення — **проєктні засоби реалізації** цих вимог; сама їхня наявність у коді не доводить відповідність вимогам без запуску в захищеному середовищі.

## Межі довіри

1. **Клієнт — API FastAPI.** JWT HS256 із `iss`, `aud`, `exp`, `iat`, `nbf` і `ver`. HTTPS/TLS — відповідальність довіреного edge proxy; без нього протокол HTTP не захищає bearer token у мережі. Ліміти на вхідні запити по клієнтському socket IP / авторизованому user ID.
2. **API — PostgreSQL.** Авторитет для користувачів, груп, `AccessGrant`, `acl_epoch`, `active_index_run_id`, `token_version`. Відкликання ACL і токенів повторно перевіряється перед відповіддю, з відомим обмеженням щодо вже надісланих байтів.
3. **PostgreSQL/local object store — Qdrant/Neo4j.** Індекси не авторитетні; метадані й entity можуть бути чутливими. У відповіді використовується лише текст chunk із підтвердженого SQL-джерела.
4. **Індекси/сховище — Ollama.** PDF і user prompt недовірені. Перед відправленням у локальну модель застосовується консервативна евристична фільтрація відомих інструкцій і regex-маскування PII. Це не semantic sandbox.
5. **Docker-хост — усі контейнери.** Наявність `internal: true` на мережі Docker та відсутність опублікованих портів БД допомагають, але не доводять ізоляцію хоста, Docker daemon та захист від SSRF у всіх сервісах.

## Таблиця загроз

| Загроза | Механізм / рішення | Автоматична перевірка | Залишковий ризик |
|---|---|---|---|
| Витік документа через чужий JWT | Підпис, issuer/audience, row-level ACL, 404 для прихованих документів | Stage 3/4 API + ACL тести | Немає зовнішнього IAM/SSO; роль admin бачить усі документи |
| Викрадені короткоживучі токени | `token_version` і `logout-all`, admin revoke | Stage 5 JWT тести | У вже активному HTTP-відповідь може бути частково відправлена |
| Brute-force паролів | Argon2, порівняння з dummy hash, 429 login per-IP | Stage 5 HTTP-тести | Лімітер в оперативній пам’яті, не між репліками; ботнет-и обходять IP limit |
| Prompt injection у запитах | Відхилення явних jailbreak-патернів | Stage 5 HTTP-тест 422 | Невідомі/обфусковані патерни пройдуть |
| Prompt injection у PDF | Недовірений контекст, видалення директивних рядків перед LLM | Stage 5 FakeChat | Необхідна adversarial evaluation; обхід regex можливий |
| PII у контексті та відповідях | Regex-маскування email, phone, IBAN у запитах, excerpts, відповіді | Stage 5 тести | Невідомі формати, зображення, PDF/OCR, семантичні ідентифікатори |
| Псевдопосилання моделі | Вимога наявності `[S1]` … `[Sn]`, перевірка діапазону | Stage 5 tests | Це не доводить, що факт реально випливає з цитованого chunk |
| Випадковий remote inference | Allowlist URL/host, httpx `trust_env=False` | Stage 5 Settings test | Host allowlist не замінює egress firewall і DNS/TLS audit |
| Зловживання API | Обмеження запитів на логін, upload, query; upload byte cap | Stage 3/5 тести | Немає WAF/edge limits; не захищає distributed-DoS |
| Host-header poisoning / cache poisoning | Allowed hosts; no-store, nosniff, frame deny | Stage 5 HTTP тести | Edge proxy і TLS не тестувалися |
| Контейнерний escape | Non-root базовий образ; read-only app FS, tmpfs, no-new-privileges, drop caps | Код/конфіг лише | Compose не запускався, реальні kernel/seccomp обмеження не перевірені |
| Компрометація секретів | Немає hard-coded токенів, конфігурація без дефолтного JWT секрету | Валідація конфігурації | Секрети досі передаються через env — потрібен Vault/Compose secrets із захищеною процедурою |

## Загальна позиція безпеки
**Stage 5 — defense-in-depth прототип.** Будь-який з guardrails може помилково заборонити легітимний запит або пропустити шкідливий. Не можна заявляти про повну відсутність витоків або відповідність ISO/GDPR/галузевим стандартам без ручної ревізії, threat modeling і penetration testing. Зберігання вихідних документів у відкритому вигляді на серверному томі залишає ризик доступу адміністратора хоста до даних.

## Що має пройти Stage 6
- Підняти реальний `docker compose` з PostgreSQL, Qdrant, Neo4j, Ollama та LangGraph.
- Перевірити egress блокування, TLS, контрольоване завантаження образів/моделей і ротацію секретів.
- Додати **зовнішній** rate limiter у proxy/Redis для кількох API реплік.
- Провести негативні сценарії ACL, role escalation, prompt injection, PII та malicious PDF.
- Додати policy-based PII detector, trace-safe logging, redaction та можливість review.
- Підготувати attack/evaluation dataset і перевірити false positives/false negatives.
- Перевірити серверний ресурсний budget, пікове навантаження, latency, p95 та error rate.
