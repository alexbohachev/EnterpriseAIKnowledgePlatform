# EAKP · Етап 2 — Детальне проєктування (v0.2)

> Дизайн, не реалізація. Документ розвиває Stage 1; офіційне завдання: `project .txt`.


# Етап 2 · Детальне проєктування архітектури

Enterprise AI Knowledge Platform (EAKP) | OTUS Architect AI/ML | Проєктна редакція v0.2 | 16.11.2026

> **Примітка:** СТАТУС: архітектуру спроєктовано, але застосунок, індекси, модель і захист ще не розгорнуто. Усі ресурси, API та метрики тут — проєктні рішення; реальні властивості підтверджуються на наступних етапах.

Цей документ продовжує PRD/SRS і C4 L1–2 із пакета EAKP Stage 1; він не замінює їх. Усі вузли та потоки на схемах означають цільовий дизайн, а не перевірений runtime.


## 0. Короткий executive summary

- Предмет проєкту: офлайн-платформа для PDF/сканів, відповідей з джерелами та GraphRAG, з дотриманням ACL на рівні документів, чанків і графових шляхів.
- Архітектура: FastAPI + LangGraph (Control Plane); PostgreSQL, object storage, Qdrant, Neo4j, локальні моделі (Data Plane).
- В етапі 2 оформлено: C4 Level 3; deployment; 3 sequence diagrams; ER; DFD Level 0 і 1; інваріанти безпеки; модель синхронізації індексів; матрицю трасованості.
- Подальша робота: реальний запуск, API, ingestion, GraphRAG, тести безпеки, репродуковані вимірювання RPS/latency/VRAM та демонстрація.


# 1. Прив’язка до вихідних вимог і рішень

| Джерело / попереднє рішення | Що деталізовано в етапі 2 |
| --- | --- |
| OTUS project.txt: 4 рівні C4 + Deployment/Sequence/ER | Для C4 L1–2 використовуємо Stage 1; створено C4 L3 + Deployment, Sequence, ER і DFD; C4 L4 (код) залишаємо наступному етапу, оскільки коду ще немає. |
| FR-01, FR-08, AT-02..05 | Policy gate + підтвердження дозволу за PostgreSQL перед LLM і перед видачею; graph provenance для кожного шляху. |
| FR-02..06, FR-10, AT-10 | Ingestion з immutable version, staging двох індексів, атомарний publication pointer та ідемпотентні jobs. |
| FR-07, FR-09, FR-11..13 | LangGraph стани, цитування/abstain, локальні моделі, tracing/metrics, offline verification. |
| ADR-0001..0005 Stage 1 | Зберігаємо статус Proposed; уточнюємо рішення новими ADR-0006..0008 без заднім числом «затверджено». |

> **Примітка:** Вимога OTUS формально просить C4 Level 1–4. Етап 2 створює Level 3; Level 4 не можна чесно зафіксувати до появи структури Python-модулів. Його сформуємо на етапі реалізації, із посиланням на фактичний код.


# 2. C4 Level 3: внутрішні компоненти оркестратора


![Рис. 1. C4 Level 3: послідовність компонентів query orchestration і контрольні точки доступу.](../diagrams/c4_level3_orchestrator.png)

*Рис. 1. C4 Level 3: послідовність компонентів query orchestration і контрольні точки доступу.*

| Компонент | Контракт / правило |
| --- | --- |
| Authorization Gate | JWT перевіряється в API; із валідованих claims отримуємо user_id і group_ids; для кожного ресурсу беремо актуальні grants з PG. |
| Query Planner | Вибирає vector і/або graph retrieval; не створює права та не підміняє user context; ліміти кількості хопів/кандидатів. |
| Retrieval Adapter | Qdrant filter — лише оптимізація; Neo4j повертає тільки evidence з provenance та index_run_id. |
| Evidence & ACL Gate | Пакетна авторитетна перевірка в PG для всіх document_version_id / chunk_id / graph edge provenance. DENY за замовчуванням. |
| Merge / Rerank | Працює виключно з уже дозволеними кандидатами; не допускає metadata та path із заборонених індексів. |
| Evidence Decision | Якщо доведених джерел недостатньо або ACL змінились, перехід до abstain/deny. |
| LLM Adapter | Викликає лише локальну модель; tool access через allowlist, без довільного SQL, мережі чи файлів. |
| Citation Validator | Перевіряє існування посилань, належність fragment/version/ACL, фінальний epoch check перед відправленням. |


## 2.1. Machine-readable state і переходи

| Поле state | Тип | Правило |
| --- | --- | --- |
| request_id, trace_id | UUID/string | Генерує API; audit не містить конфіденційного payload. |
| principal | VerifiedPrincipal | Ніколи не береться з user-supplied JSON. |
| question | string | Довжина й тип валідуються; текст не потрапляє до стандартного логу. |
| acl_snapshot | doc_id → acl_epoch | Використовується для final revalidation; не дає доступу сам собою. |
| candidate_ids | list<chunk_id> | IDs з Qdrant/Neo4j без сирого тексту. |
| evidence | list<AuthorizedEvidence> | Тільки chunk/page/version із дозволом у PG. |
| answer,citations | string,list | Заповнюються після генерації та citation gate. |
| decision | allow/deny/abstain | Fail-closed при збої ACL або storage. |

Гілки: validate_identity → authorize_query → retrieve → verify_acl → evidence_sufficient? → [generate → validate_citations → revalidate_acl → respond] АБО [abstain]. Стан не має переходу generate до verify_acl. Всі повторні спроби retrieval обмежені, а authorization failure не retry-иться як success.


# 3. Deployment Diagram: фізичне розміщення та кордони довіри


![Рис. 2. Пропоноване одновузлове On-Premise MVP (логічна сегментація мережі).](../diagrams/deployment.png)

*Рис. 2. Пропоноване одновузлове On-Premise MVP (логічна сегментація мережі).*

> **Примітка:** Зображені DMZ / App / Data / Ops — логічні trust zones. Сам по собі Docker Compose не є гарантією повноцінного air-gap. Потрібні фізична/мережева ізоляція або host firewall + явна перевірка заборони egress; це ще не реалізовано.

| Зона | Контейнери / інтерфейси | Обмеження |
| --- | --- | --- |
| Ingress / DMZ | Internal TLS reverse proxy, UI | Тільки 443 із дозволеної мережі; жодного порту DB/LLM назовні. |
| App / Control Plane | FastAPI; LangGraph; ingestion worker | Мережевий доступ лише до визначених backend / storage портів; IAM та policy в API. |
| Data Plane | PostgreSQL, object storage, Qdrant, Neo4j | Persistent encrypted-at-rest volumes за політикою; відокремлені credentials/службові accounts. |
| Local model runtime | LLM server, embeddings/OCR (CPU/GPU) | Без зовнішнього API/завантажень; bind тільки на internal iface; GPU optional до сайзингу. |
| Ops | OTel Collector, dashboard, audit metadata | Окремий операторський доступ; не зберігати сирі контексти/PII. |
| Offline boundary | Firewall, локальний image/model cache | DENY runtime egress; checksum/SBOM і контрольована процедура перенесення образів. |


## 3.1. Попередня матриця портів та розгортання

| From | To | Протокол | Правило |
| --- | --- | --- | --- |
| Browser (LAN) | Reverse proxy | HTTPS:443 | Allow (internal only) |
| Reverse proxy | FastAPI | HTTP:8000 (internal) | Allow; not exposed |
| FastAPI / worker | PostgreSQL | TCP:5432 | Allow; scoped DB roles |
| Worker | Object Storage | S3-compatible:9000 | Allow; private network only |
| Retriever | Qdrant | HTTP/gRPC private:6333/6334 | Allow; no public bind |
| Retriever | Neo4j | Bolt:7687 | Allow; no public bind |
| Orchestrator/worker | Model serving | HTTP private (TBD) | Allow; auth at internal boundary |
| Any runtime | Public internet | any | Deny & test (Stage 3+) |

Сайзинг TBD: CPU/RAM/GPU VRAM, середня/пікова кількість запитів, токени на запит, кількість сторінок та OCR rate. До вимірювань не обіцяємо жодних p95 чи RPS; обсяги томів також залишаються відкритими. HA, резервні ЦОДи, DR та Kubernetes не входять у MVP.


# 4. Sequence Diagram A: authorized query


![Рис. 3. Авторизований запит із двома перевірками доступу та валідацією цитат.](../diagrams/sequence_query.png)

*Рис. 3. Авторизований запит із двома перевірками доступу та валідацією цитат.*

- API перевіряє підпис, issuer, audience, exp, ролі, scope; ніколи не довіряє значенням user_id із body.
- Qdrant/Neo4j повертають candidate IDs; кожен графовий шлях повинен мати lineage до документної версії та чанка.
- База PostgreSQL є єдиним джерелом актуальних ACL; prefilter індексу не заміняє postfilter.
- Відповідь з citations віддається тільки після validation; при нестачі evidence — чесний abstain.
- Під час MVP відкладений streaming відповіді до перевірки ACL; інакше revocation race здатна спричинити витік.


# 5. Sequence Diagram B: ingestion та синхронізація індексів


![Рис. 4. Створення immutable document version, staging та atomic publish.](../diagrams/sequence_ingestion.png)

*Рис. 4. Створення immutable document version, staging та atomic publish.*

| Статус ingestion | Дозволений перехід / правило |
| --- | --- |
| PENDING | Job створено разом з document_version; worker claim через FOR UPDATE SKIP LOCKED. |
| PROCESSING | Lease з expires_at; після crash lease повертає завдання до повторної спроби. |
| INDEXING | Qdrant + Neo4j staging записи позначені index_run_id, doc_version_id; не видимі запитам. |
| VERIFYING | Контроль count/checksum/provenance обох індексів, fail closed. |
| READY | Єдина PG-транзакція переводить document.active_index_run_id → новий run; лише тоді індекс стає активним. |
| FAILED | Помилка з reason_code; capped retry, backoff, cleanup staging. Не видаляти останню справну версію. |

> **Примітка:** Між Qdrant і Neo4j немає спільної транзакції. Атомарність для читача забезпечує PG publication pointer: запит повертає лише записи index_run_id, які дорівнюють активному run. Це design intent; реалізацію необхідно перевірити на crash/retry сценаріях.


# 6. Sequence Diagram C: відкликання доступу під час запиту


![Рис. 5. Конкурентна зміна ACL: відмова перед передаванням відповіді.](../diagrams/sequence_acl_revoke.png)

*Рис. 5. Конкурентна зміна ACL: відмова перед передаванням відповіді.*

ACL revoke виконується транзакційно у PostgreSQL: змінити grant, збільшити documents.acl_epoch, зафіксувати audit event. Для запиту, що розпочався раніше, порівняти epoch перед генерацією або видачею. Якщо epoch змінився — повторити authoritative authorization; заборонити доставку старого response. Для безпечного MVP не здійснюємо streaming до фінального gate.


# 7. ER Diagram: логічна реляційна модель


![Рис. 6. PostgreSQL: суб’єкти, права, документи, версії, чанки, завдання, provenance та аудит.](../diagrams/er_model.png)

*Рис. 6. PostgreSQL: суб’єкти, права, документи, версії, чанки, завдання, provenance та аудит.*

| Сутність | Ключові поля / інваріанти |
| --- | --- |
| users, groups, group_membership | subject_id у users унікальний; group membership керується локально/через IdP adapter. |
| documents | document_id (PK), owner_id, classification, acl_epoch, active_index_run_id NULL до першого READY. |
| document_versions | version_id (PK), doc_id (FK), sha256, object_uri, created_at; immutable після publish. |
| access_grants | doc_id, principal_type (user/group), principal_id, permission (read/write/admin), revoked_at; deny precedence за політикою. |
| ingestion_jobs | job_id, version_id, status, lease_until, attempts, index_run_id, failure_code; унікальність по run. |
| chunks | chunk_id, version_id, page_number, ordinal, text_object_uri, index_run_id; FK на документну версію. |
| entity_mentions | mention_id, chunk_id, normalized_label, span; graph entities посилаються на ці згадки. |
| audit_events | actor_user_id, action, decision, target_id, trace_id, timestamp; без сирих документів. |


## 7.1. Neo4j / Qdrant як похідні read models

- Qdrant payload: vector_id, chunk_id, document_id, document_version_id, index_run_id, page_number, chunk_ordinal, classification. Жоден запис Qdrant не є джерелом істини щодо дозволу.
- Neo4j labels: Document, Chunk, Entity. Edge types: HAS_CHUNK, MENTIONS, RELATED_TO. Кожне Entity та RELATED_TO має документно-локальний scope й provenance (source_chunk_id, document_version_id, index_run_id).
- GraphRAG multi-hop: обхід по allowlist документів; кожен edge перевіряється за provenance. Не глобалізувати Entity під одним ім’ям по всій базі без перевірки дозволів — це ризик витоку metadata.
- Контекст між документами: об’єднання сутностей можливе лише у query-scoped віртуальному графі, вже після відбору доступних документів.
- Зміна ACL не потребує синхронної перебудови індексів, бо авторитетний gate читає PG. Видалення документа має прибрати похідні записи та об’єкти асинхронно після deny.


## 7.2. Рекомендовані ключі та індекси

| Об’єкт | Constraint / індекс |
| --- | --- |
| documents | PK (document_id), INDEX (owner_id), acl_epoch default 0 |
| access_grants | UNIQUE(document_id, principal_type, principal_id, permission) WHERE revoked_at IS NULL |
| document_versions | UNIQUE(document_id, sha256) для дедуплікації незмінних версій (політика версіонування вирішується окремо) |
| ingestion_jobs | INDEX(status, lease_until), UNIQUE(index_run_id), attempt_count >= 0 |
| chunks | UNIQUE(version_id, ordinal), INDEX(version_id,page_number), PK(chunk_id) |
| Qdrant | payload indexes для document_id, version_id, index_run_id |
| Neo4j | UNIQUE Document.document_version_id, UNIQUE Chunk.chunk_id; scoped Entity identity за (version_id, local_id) |


# 8. DFD Level 0: зовнішні актори, дані та trust boundaries


![Рис. 7. Система як єдиний процес та класифіковані потоки; egress заборонений.](../diagrams/dfd_level0.png)

*Рис. 7. Система як єдиний процес та класифіковані потоки; egress заборонений.*


# 9. DFD Level 1: ingestion, retrieval, evidence gate


![Рис. 8. Деталізація DFD: різні шляхи запису і читання, одна політика доступу.](../diagrams/dfd_level1.png)

*Рис. 8. Деталізація DFD: різні шляхи запису і читання, одна політика доступу.*

| Потік | Дані | Правило мінімізації |
| --- | --- | --- |
| T1/T2: client → API | JWT, question/PDF, grant change | TLS, size/type validation; body не логувати. |
| F1: PG | ACL, jobs, document metadata, audit | RBAC DB, транзакційна зміна ACL; PII мінімум. |
| F2: Object Store | Original PDF, OCR text, large chunk contents | Private buckets, per-document object keys; presigned access тільки через policy. |
| F3: Qdrant/Neo4j | Embeddings, nodes/edges with provenance | Index_run/version scopes; avoid raw secrets in labels/metadata. |
| F4: model runtime | Allowed evidence, prompt, generated answer | Local-only, no public endpoints; не зберігати full prompts у telemetry. |
| T3: output | Answer, verified source citations, trace_id | Revalidation ACL/epoch; never include denied labels/edges. |


# 10. Вимоги до API та failure behavior

| Операція | Успіх | Failure / security rule |
| --- | --- | --- |
| POST /api/v1/documents | 201/202 {document_id, job_id} | 413 розмір; 415 unsupported PDF; 401/403; checksum; owner з identity. |
| GET /api/v1/jobs/{id} | 200 {status, attempt_count,...} | 404 на невідомий або чужий job (anti-enumeration). |
| POST /api/v1/query | 200 {answer,citations,abstained,trace_id} | 403 auth fail; 200 abstained=true без доказів; 503 when policy store unavailable. |
| POST /api/v1/documents/{id}/acl | 200 {document_id,acl_epoch} | 403 для не-owner/admin; epoch increment transactional. |
| GET /api/v1/documents/{id} | 200 minimal metadata | 404 on missing OR unauthorized to reduce existence leakage. |
| GET /healthz; GET /metrics | Health minimal; metrics ops only | Не відкривати provider IDs, prompts, document titles. |


# 11. Security / correctness: інваріанти

- INV-01: Жоден LLM prompt не містить тексту chunk, для якого немає актуального READ-дозволу від PostgreSQL.
- INV-02: Жоден графовий вузол/ребро не може бути підставою відповіді без дозволеного source_chunk_id та active_index_run_id.
- INV-03: ACL revoke не може відкрити старі cached/index permissions; кеш дозволів не є авторитетним.
- INV-04: Жоден неактивний index_run_id не бере участі у відповіді (staging/failed).
- INV-05: Кожна citation валідна для видимої document_version і page_no, user має READ на момент видачі.
- INV-06: За помилки Postgres/ACL сервіс відмовляє — не повертається best-effort з неавторизованим вмістом.
- INV-07: Документні інструкції — дані, а не правила; недовірені PDF не можуть викликати непередбачені tools.
- INV-08: Offline runtime: no public API calls; перевірка egress виконується окремо.


# 12. План перевірок архітектури (тести ще НЕ запускали)

| Test ID | Підготовка / дія | Очікування |
| --- | --- | --- |
| AT-02 | B шукає секретний фрагмент A у Qdrant | 0 candidate evidence у prompt/citations. |
| AT-03 | B робить multi-hop запит через Entity від A | Немає назви, зв’язку, graph path від A. |
| AT-04 | Owner revoke A під час генерації | No output until authorization recheck; deny/retry. |
| AT-06 | PDF містить prompt injection / tool directive | LLM не може керувати ACL або зовнішніми запитами. |
| AT-08 | Blocked runtime egress, restart services | Ingestion/query працюють без internet; no DNS leak. |
| AT-09 | Load test 1/5/10 concurrency | Звіт p50/p95/p99, RPS, TPS, VRAM, hardware/model. |
| AT-10 | Worker crash after Qdrant write, before Neo4j | Старий index_run_id лишається активним; idempotent retry. |
| ST-01 | Qdrant/Neo4j скомпрометовано stale ACL | PG postfilter blocks unauthorized data. |
| ST-02 | Concurrent upload of same PDF checksum | No duplicate active chunks after retries. |
| ST-03 | Qdrant timeout or PG unavailable | 503/abstain; never fall back to unverified context. |


# 13. Ризики, рішення та відкриті питання

| ID / ризик | Контроль / що потрібно довести |
| --- | --- |
| R1: GraphRAG перетинає ACL | Document-scoped entities + edge provenance; негативні graph tests. |
| R2: міжбазова неузгодженість | Staging і атомарний active_index_run_id; crash/retry tests. |
| R3: модель не вміщується у VRAM | Вибір model+quantization тільки після inventory/bench; CPU fallback з latency impact. |
| R4: pseudo-airgap через Docker | Host firewall/physical isolation, pre-staged artifacts, network egress test. |
| R5: некоректні цитати / hallucinations | Citation registry, verification, abstain, human eval; нуль гарантій абсолютної безпомилковості. |
| R6: зберігання PII/secret у telemetry | Structured redacted logs, sampling controls, privacy review. |
| R7: OCR креслень / діаграм неповний | MVP: текстові та скановані PDF; складні графічні елементи — optional extension. |
| R8: високий operational overhead | Compose single-node у MVP; порівняння з K8s після отримання метрик. |


# 14. Контрольний список до початку етапу 3

- [ ] Визначити фактичні GPU/CPU/RAM/SSD, локальний model cache і дозволений test corpus.
- [ ] Уточнити політику reader/owner/admin і груп, вимоги до SSO, retention і backup.
- [ ] Затвердити документно-локальні graph entities і транзакційний acl_epoch.
- [ ] Підготувати offline Docker image/model manifest із checksum (без секретів).
- [ ] Створити FastAPI skeleton, Postgres schema migrations, worker stub, local volume mounts.
- [ ] Почати з AT-02/03/04 та fail-closed behavior до підключення LLM.
- [ ] Закріпити фактичні image/model версії після smoke test (не вигадувати бенчмарки).


# 15. Матриця відповідності та Definition of Done етапу 2

| Артефакт | Результат / шлях | Доказ |
| --- | --- | --- |
| C4 Level 3 | diagrams/c4_level3_orchestrator.dot/svg/png | Компоненти, стани, policy gates. |
| Deployment | diagrams/deployment.dot/svg/png | Зони, GPU, storage, private ports, egress. |
| Sequence | 3 файли: query, ingestion, ACL revoke | Happy, error, concurrency/race сценарії. |
| ER | diagrams/er_model.dot/svg/png | Principal/ACL, versions, chunks, jobs, audit. |
| DFD | diagrams/dfd_level0 та dfd_level1.* | Класифіковані потоки, trust boundary. |
| ADRs | docs/adr/ADR-0006..0008.md | Відстежувані proposed decision records. |
| Backlog | docs/Stage3_Backlog.md | Майбутні етапи мають acceptance checks. |
| Implementation | ПОКИ НЕ ВИКОНАНО | Застосунок не запускався, тестів/бенчмарків немає. |


# Джерела, припущення та статус

Першоджерела: (1) завдання OTUS Architect AI/ML «project .txt»; (2) транскрипції №32, №33, №34 про проєкт та захист; (3) EAKP Stage 1 — PRD/SRS, C4 L1/L2, ADR-0001..0005. Проєктні вибори в цьому документі — авторська архітектурна пропозиція, що може бути переглянута після hardware inventory, security review і запуску. Жодна метрика не заявляється як виміряна. «OTUS» не означає офіційне схвалення дизайну.
