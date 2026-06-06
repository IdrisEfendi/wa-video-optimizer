# WhatsApp Video Optimizer

Simple web app untuk menganalisis dan mengoptimalkan video sebelum dikirim ke WhatsApp.

## Requirements

- Python 3.10+
- FFmpeg dan FFprobe tersedia di `PATH`

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Buka:

```text
http://127.0.0.1:8000
```

## Storage

Tidak ada login dan tidak ada database. Metadata job disimpan sebagai JSON di `storage/jobs`.
