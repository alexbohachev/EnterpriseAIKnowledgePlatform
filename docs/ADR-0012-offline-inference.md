# ADR-0012 — Local Ollama inference adapters

Status: Accepted for development only.

Decision: Ollama `/api/embed` with bge-m3 (configured dim=1024) and `/api/chat` with qwen2.5:3b. LAN-only Compose endpoints; no hosted LLM APIs. Production high throughput may migrate to vLLM/SGLang based on measured GPU benchmarks.

Risks: model weights/image preloading, local CPU slowness, output hallucinations and prompt injection, security of the container network. Fail closed when unavailable; no mock output in production.
