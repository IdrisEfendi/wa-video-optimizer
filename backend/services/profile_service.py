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
