# release-summarizer

Teknoloji projelerinin GitHub release'lerini haftalık takip eden, AI ile özetleyen ve HTML e-posta raporu oluşturan servis.
OpenAI modelleri yanı sıra **LiteLLM** entegrasyonu sayesinde Anthropic, Google Gemini, Mistral ve self-hosted (Ollama, LM Studio, vLLM) modeller de kullanılabilir.

## Çalışma Şekli

- Tüm kaynaklar **aynı anda paralel** çekilir (`asyncio.gather` + `Semaphore(4)` ile AI çağrıları throttle edilir)
- Her kaynakta önce GitHub'dan son sürüm tag'ı alınır, **DB'deki bilinen sürümle karşılaştırılır**
- Sürüm değişmemişse o kaynak için **AI'ya hiç gidilmez** — sadece değişen kaynaklar özetlenir
- Hiç yeni sürüm yoksa rapor oluşturulmaz, job başarıyla çıkar

## Gereksinimler

- Python **3.12+**
- Docker & Docker Compose (veya OpenShift)

## Nasıl Çalışır

1. Aktif kaynakların GitHub release'leri paralel çekilir
2. Yeni release varsa OpenAI ile Türkçe özet üretilir (yeni release yoksa OpenAI çağrısı yapılmaz)
3. Tüm özetler HTML e-posta formatında birleştirilir ve DB'ye kaydedilir

## Varsayılan Kaynaklar

MLflow · Qdrant · OpenShift AI · Red Hat AI (InstructLab) · Ray · KServe · Docker · Kubernetes

## Kurulum

### Docker

```bash
docker build -t release-summarizer .

# API sunucusu
docker run -d \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -p 8000:8000 \
  release-summarizer

# Tek seferlik rapor (CronJob modu)
docker run --rm \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  release-summarizer python job.py
```

### uv ile lokal

```bash
cp .env-example .env
# .env içine gerekli değişkenleri gir (OpenAI veya LiteLLM)

uv sync # bağımlılıkları yükler, .venv + uv.lock oluşturur

# API sunucusu
uv run uvicorn app.main:app --reload

# Ya da sadece rapor üretmek için
uv run python job.py
```

### pip ile lokal

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

## Çevre Değişkenleri

| Değişken | Zorunlu | Varsayılan | Açıklama |
|---|---|---|---|
| `OPENAI_API_KEY` | OpenAI kullanılıyorsa ✅ | — | OpenAI API anahtarı |
| `MODEL` | | `gpt-4o-mini` | Kullanılacak model (OpenAI için model adı, LiteLLM için `provider/model` formatı) |
| `LITELLM_API_KEY` | LiteLLM kullanılıyorsa ✅ | — | Sağlayıcıya ait API anahtarı veya proxy master key |
| `LITELLM_BASE_URL` | | — | Self-hosted LiteLLM proxy adresi (örn. `http://localhost:4000`) |
| `GITHUB_TOKEN` | | — | GitHub rate limit için (opsiyonel) |
| `MAX_CONCURRENT_AI` | | `4` | Paralel AI çağrısı limiti |
| `SOURCE_TIMEOUT` | | `90` | Kaynak başına timeout (saniye) |

## Model Seçimi

Model adında `/` varsa veya `LITELLM_API_KEY` set edilmişse **LiteLLM** devreye girer, aksi hâlde native OpenAI client kullanılır.

### OpenAI

```env
OPENAI_API_KEY=sk-proj-xxxx
MODEL=gpt-4o-mini
```

### Anthropic Claude

```env
LITELLM_API_KEY=sk-ant-xxxx
MODEL=anthropic/claude-3-5-sonnet-20240620
```

### Google Gemini

```env
LITELLM_API_KEY=AIza-xxxx
MODEL=gemini/gemini-1.5-pro
```

### Self-hosted LiteLLM Proxy (Ollama, LM Studio, vLLM)

```env
LITELLM_BASE_URL=http://localhost:4000
LITELLM_API_KEY=<proxy-master-key>
MODEL=qwen3.5-9b
```

> LiteLLM desteklediği tüm sağlayıcılar için: https://docs.litellm.ai/docs/providers

## API

| Method | Path | Açıklama |
|---|---|---|
| `POST` | `/reports/generate` | Rapor oluştur |
| `GET` | `/reports/{id}/html` | Raporu tarayıcıda görüntüle |
| `GET` | `/sources/` | Kaynakları listele |
| `POST` | `/sources/` | Yeni kaynak ekle |
| `PATCH` | `/sources/{id}/toggle` | Kaynak aktif/pasif |

Swagger UI: `http://localhost:8000/docs`

## HTML Rapora Erişim

Rapor oluşturulduktan sonra dönen `id` ile tarayıcıda doğrudan görüntülenebilir:

```bash
# 1. Rapor oluştur
curl -X POST http://localhost:8000/reports/generate

# Dönen yanıttaki id'yi kullan:
# {"id": "abc123", "created_at": "...", ...}

# 2. Tarayıcıda aç
open http://localhost:8000/reports/abc123/html
```

Son raporları listelemek için:
```bash
curl http://localhost:8000/reports/
```

## Veritabanı

SQLite (`data/releases.db`) — üç tablo:

### `sources` — takip edilen kaynaklar
| Sütun | Tip | Açıklama |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | String | Görünen ad |
| `slug` | String (unique) | URL tanımlayıcısı |
| `source_type` | `github` / `url` | Kaynak tipi |
| `config` | JSON | `{"repo": "org/repo"}` veya `{"url": "..."}` |
| `enabled` | Boolean | Aktif/pasif |

### `releases` — çekilen sürümler
| Sütun | Tip | Açıklama |
|---|---|---|
| `id` | UUID | Primary key |
| `source_id` | UUID | Bağlı kaynak |
| `version` | String | Tag adı (ör. `v1.2.3`) |
| `body` | Text | Ham release notları |
| `summary` | Text | AI özeti (sadece latest release'de dolu) |
| `url` | String | Release sayfası linki |
| `published_at` | DateTime | GitHub'daki yayın tarihi |
| `fetched_at` | DateTime | Çekilme zamanı |

### `reports` — oluşturulan raporlar
| Sütun | Tip | Açıklama |
|---|---|---|
| `id` | UUID | Primary key |
| `content` | Text | Tam HTML içerik |
| `created_at` | DateTime | Oluşturulma zamanı |
| `release_ids` | JSON | Rapora dahil edilen release id listesi |

## Yeni Kaynak Ekleme

**GitHub repo:**
```json
{"name": "LangChain", "slug": "langchain", "source_type": "github", "config": {"repo": "langchain-ai/langchain"}}
```

**URL / RSS:**
```json
{"name": "Red Hat Blog", "slug": "redhat-blog", "source_type": "url", "config": {"url": "https://example.com/rss"}}
```

## OpenShift CronJob

```bash
docker build -t nexus.example.com/release-summarizer:1.0.0 .
docker push nexus.example.com/release-summarizer:1.0.0
```

CronJob manifest'inde:
```yaml
command: ["python", "job.py"]
schedule: "0 7 * * 1"  # Her Pazartesi 07:00
```

## Proje Yapısı

```
app/
├── core/        # config, database
├── db/          # modeller, seed kaynakları
├── agents/      # AI Agents — OpenAI veya LiteLLM (fetch, summarize, compose)
├── services/    # FastAPI'den bağımsız iş mantığı
└── routers/     # API endpoint'leri
job.py           # Standalone CronJob entrypoint
examples/
└── sample-report.html  # Örnek HTML rapor çıktısı
```
