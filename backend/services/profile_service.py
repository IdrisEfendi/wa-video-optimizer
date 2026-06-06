from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    name: str
    crf: int
    maxrate_720: str
    maxrate_1080: str
    story: bool = False
    status: bool = False


PROFILES = {
    "standard": Profile("standard", 24, "2500k", "4500k"),
    "hd": Profile("hd", 21, "3500k", "6000k"),
    "status": Profile("status", 23, "3000k", "4000k", status=True),
    "story": Profile("story", 22, "3500k", "6000k", story=True),
}


def even(value: int) -> int:
    return max((value // 2) * 2, 2)


def get_profile(name: str | None) -> Profile:
    key = (name or "standard").lower()
    if key not in PROFILES:
        raise ValueError("Profile optimasi tidak valid.")
    return PROFILES[key]


def output_fps(metadata: dict) -> float:
    fps = float(metadata.get("fps") or 0)
    if fps <= 0:
        return 30
    return min(fps, 30)


def video_filter(metadata: dict, profile: Profile) -> str:
    width = int(metadata.get("width") or 0)
    height = int(metadata.get("height") or 0)
    is_vertical = height > width

    if profile.story:
        return "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1"

    if profile.status and is_vertical:
        return "scale='if(gt(ih,1280),-2,iw)':'if(gt(ih,1280),1280,ih)':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1"

    if width > 1920 or height > 1080:
        return "scale=1920:1080:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1"

    return "scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1"


def bitrate_cap(metadata: dict, profile: Profile) -> tuple[str, str]:
    height = int(metadata.get("height") or 0)
    maxrate = profile.maxrate_720 if height <= 720 else profile.maxrate_1080
    numeric = int(maxrate.rstrip("k"))
    return maxrate, f"{numeric * 2}k"


def _fit_inside(width: int, height: int, max_width: int, max_height: int, upscale: bool = False) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        return 0, 0
    scale = min(max_width / width, max_height / height)
    if not upscale:
        scale = min(scale, 1)
    return even(int(width * scale)), even(int(height * scale))


def output_resolution(metadata: dict, profile: Profile) -> tuple[int, int]:
    width = int(metadata.get("width") or 0)
    height = int(metadata.get("height") or 0)
    is_vertical = height > width

    if profile.story:
        return 1080, 1920

    if profile.status and is_vertical:
        return _fit_inside(width, height, width, 1280, upscale=False)

    if width > 1920 or height > 1080:
        return _fit_inside(width, height, 1920, 1080, upscale=False)

    return even(width), even(height)


def estimate_settings(metadata: dict, profile_name: str | None) -> dict:
    profile = get_profile(profile_name)
    width = int(metadata.get("width") or 0)
    height = int(metadata.get("height") or 0)
    fps = float(metadata.get("fps") or 0)
    target_width, target_height = output_resolution(metadata, profile)
    target_fps = output_fps(metadata)
    maxrate, bufsize = bitrate_cap({"height": target_height}, profile)
    duration = float(metadata.get("duration") or 0)
    file_size = int(metadata.get("file_size") or 0)
    maxrate_kbps = int(maxrate.rstrip("k"))
    audio_kbps = 128

    estimated_bytes = int(((maxrate_kbps + audio_kbps) * 1000 / 8) * duration) if duration > 0 else 0
    estimated_low = int(estimated_bytes * 0.65) if estimated_bytes else 0
    estimated_high = int(estimated_bytes * 1.05) if estimated_bytes else 0

    changes = []
    if fps > 30:
        changes.append("FPS diturunkan ke 30.")
    if target_width != width or target_height != height:
        changes.append(f"Resolusi output menjadi {target_width}x{target_height}.")
    if profile.story:
        changes.append("Output dibuat vertikal 9:16 dengan padding jika diperlukan.")
    if not changes:
        changes.append("Resolusi dan FPS utama dipertahankan.")

    warnings = []
    if duration >= 300:
        warnings.append("Video lebih dari 5 menit, proses optimasi bisa cukup lama.")
    if file_size >= 250 * 1024 * 1024:
        warnings.append("File lebih dari 250 MB, upload dan encoding bisa memakan waktu.")
    if width >= 3840 or height >= 2160:
        warnings.append("Video 4K akan diturunkan ke batas WhatsApp agar kompresi lebih stabil.")
    if float(metadata.get("bitrate") or 0) <= 1_000_000 and width >= 1280:
        warnings.append("Bitrate sumber relatif rendah; optimasi tidak bisa mengembalikan detail yang sudah hilang.")

    return {
        "profile": profile.name,
        "video_codec": "libx264",
        "audio_codec": "aac",
        "container": "mp4",
        "crf": profile.crf,
        "preset": "medium",
        "fps": target_fps,
        "width": target_width,
        "height": target_height,
        "resolution": f"{target_width}x{target_height}",
        "maxrate": maxrate,
        "bufsize": bufsize,
        "audio_bitrate": "128k",
        "audio_channels": "stereo",
        "audio_sample_rate": "44100 Hz",
        "movflags": "+faststart",
        "changes": changes,
        "warnings": warnings,
        "estimated_size": {
            "low_bytes": estimated_low,
            "high_bytes": estimated_high,
            "basis": "Perkiraan kasar dari maxrate video, audio 128k, dan durasi. CRF bisa menghasilkan ukuran aktual berbeda.",
        },
    }
