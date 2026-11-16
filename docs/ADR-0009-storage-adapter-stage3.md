# ADR-0009 — Тимчасове файлове сховище Stage 3

**Статус:** Accepted for *development MVP only*. **Дата:** 2026-11-16.

## Контекст

Stage 2 передбачає S3-сумісний object storage і безпечне походження document/chunk/version. Для перевірки FastAPI, ACL і ingestion без розгортання всього стека потрібен мінімальний adapter.

## Рішення

У Stage 3 застосувати локальний persistent Docker volume зі згенерованими UUID object keys. Зберігати SHA256 і ключ у PostgreSQL, а вміст — тільки у приватному тому. Жодних прямих статичних URL. Через `app/storage.py` зберегти точку заміни на MinIO/S3 у Stage 4.

## Компроміси

Простіше тестувати й налагоджувати, але немає HA, object versioning, bucket IAM або гарантованої атомарності PostgreSQL+filesystem. Не позиціонувати як production-ready protected storage.

## Верифікація

Тести upload, immutable metadata, ACL, revoke, secure object key і worker. Повний offline/air-gap / secret scanning — окреме приймання після Stage 4–6.
