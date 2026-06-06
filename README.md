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

## Configuration

Runtime config dibaca dari environment variable:

```bash
set WA_MAX_UPLOAD_MB=500
set WA_JOB_EXPIRY_HOURS=24
set WA_MAX_CONCURRENT_JOBS=1
set WA_FFMPEG_BIN=ffmpeg
set WA_FFPROBE_BIN=ffprobe
```

Endpoint `GET /api/config` menampilkan config aktif.

## Maintenance API

- `GET /api/health` mengecek FFmpeg, FFprobe, dan storage usage.
- `GET /api/config` menampilkan max upload size, expiry hours, concurrent jobs, dan path binary FFmpeg/FFprobe.
- `GET /api/estimate/{job_id}?profile=standard` menampilkan estimasi setting output sebelum optimasi.
- `POST /api/jobs/{job_id}/cancel` meminta pembatalan job yang sedang diproses.
- `POST /api/cleanup` menghapus job yang sudah melewati `expires_at`.
- `DELETE /api/jobs/{job_id}` menghapus job tertentu jika tidak sedang diproses.

## Validation

Upload ditolak jika file tidak bisa dibaca FFprobe, tidak memiliki stream video, durasi tidak valid, resolusi `0x0`, FPS tidak valid, atau ukuran melebihi 500 MB.

Status proses: `uploaded`, `queued`, `encoding`, `finalizing`, `cancel_requested`, `canceled`, `completed`, `failed`.

Estimasi output menampilkan perkiraan ukuran kasar dan warning untuk video panjang, file besar, 4K, atau sumber bitrate rendah.

## Tests

```bash
python -m unittest discover -s tests
```
