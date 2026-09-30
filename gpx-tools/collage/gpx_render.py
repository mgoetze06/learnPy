from __future__ import annotations

import argparse
import importlib.util
import json
import math
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


def _sanitize_output_path(path: str | Path) -> Path:
    target = Path(path)
    cleaned_name = target.name.strip("\"'")
    cleaned_name = cleaned_name.strip()
    cleaned_name = "".join(ch for ch in cleaned_name if ch not in '<>:"/\\|?*')
    cleaned_name = cleaned_name.rstrip(" .")
    if not cleaned_name:
        raise ValueError(f"Output path resolves to an invalid filename: {path}")
    return target.with_name(cleaned_name)


def _load_strava_heatmap_module():
    heatmap_path = Path(__file__).resolve().parents[1] / "heatmap" / "strava_local_heatmap_map.py"
    if not heatmap_path.exists():
        raise FileNotFoundError(f"Strava heatmap module not found: {heatmap_path}")

    spec = importlib.util.spec_from_file_location("strava_local_heatmap_map", heatmap_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {heatmap_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    _HEATMAP_MODULE = _load_strava_heatmap_module()
    generate_heatmap_from_points = _HEATMAP_MODULE.generate_heatmap_from_points
except FileNotFoundError:
    _HEATMAP_MODULE = None
    generate_heatmap_from_points = None


def extract_gpx_points(gpx_path: str | Path | None) -> list[tuple[float, float]]:
    if gpx_path is None:
        return []

    path = Path(gpx_path)
    if not path.exists():
        return []

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []

    points: list[tuple[float, float]] = []
    for element in root.iter():
        if not element.tag.endswith("trkpt"):
            continue
        lat = element.attrib.get("lat")
        lon = element.attrib.get("lon")
        if lat is None or lon is None:
            continue
        try:
            points.append((float(lat), float(lon)))
        except ValueError:
            continue

    return points


def parse_gpx_activity(gpx_path: str | Path | None) -> dict[str, str | float | int]:
    if gpx_path is None:
        return {"date": "Unknown date", "distance_km": 0.0, "climbing_m": 0, "duration_text": "00:00:00"}

    path = Path(gpx_path)
    if not path.exists():
        return {"date": "Unknown date", "distance_km": 0.0, "climbing_m": 0, "duration_text": "00:00:00"}

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return {"date": "Unknown date", "distance_km": 0.0, "climbing_m": 0, "duration_text": "00:00:00"}

    point_data: list[dict[str, float | str]] = []
    for trkpt in root.iter():
        if not trkpt.tag.endswith("trkpt"):
            continue
        lat = trkpt.attrib.get("lat")
        lon = trkpt.attrib.get("lon")
        if lat is None or lon is None:
            continue
        ele = 0.0
        time_value = ""
        for child in list(trkpt):
            if child.tag.endswith("ele"):
                try:
                    ele = float(child.text or 0)
                except (TypeError, ValueError):
                    ele = 0.0
            elif child.tag.endswith("time"):
                time_value = (child.text or "").strip()
        point_data.append({"lat": float(lat), "lon": float(lon), "ele": ele, "time": time_value})

    if not point_data:
        return {"date": "Unknown date", "distance_km": 0.0, "climbing_m": 0, "duration_text": "00:00:00"}

    distance_km = 0.0
    ascent_m = 0.0
    for current, nxt in zip(point_data, point_data[1:]):
        lat1, lon1 = float(current["lat"]), float(current["lon"])
        lat2, lon2 = float(nxt["lat"]), float(nxt["lon"])
        rad = math.radians
        dlat = rad(lat2 - lat1)
        dlon = rad(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km += 6371.0 * c
        if float(nxt["ele"]) > float(current["ele"]):
            ascent_m += float(nxt["ele"]) - float(current["ele"])

    start_time = ""
    end_time = ""
    for point in point_data:
        if point["time"]:
            if not start_time:
                start_time = str(point["time"])
            end_time = str(point["time"])

    duration_seconds = 0
    if start_time and end_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            duration_seconds = max(int((end_dt - start_dt).total_seconds()), 0)
        except ValueError:
            duration_seconds = 0

    date_value = "Unknown date"
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            date_value = start_dt.strftime("%Y-%m-%d")
        except ValueError:
            date_value = start_time[:10] if len(start_time) >= 10 else "Unknown date"

    hours, remainder = divmod(duration_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    duration_text = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    return {"date": date_value, "distance_km": round(distance_km, 1), "climbing_m": int(round(ascent_m)), "duration_seconds": duration_seconds, "duration_text": duration_text}


def project_gpx_points(points: Iterable[tuple[float, float]], width: int, height: int, margin: int = 60) -> list[tuple[float, float]]:
    points = list(points)
    if not points:
        return []

    min_lat = min(lat for lat, _ in points)
    max_lat = max(lat for lat, _ in points)
    min_lon = min(lon for _, lon in points)
    max_lon = max(lon for _, lon in points)
    span_lat = max(max_lat - min_lat, 1e-6)
    span_lon = max(max_lon - min_lon, 1e-6)
    scale = min((width - 2 * margin) / span_lon, (height - 2 * margin) / span_lat) if width > 0 and height > 0 else 1.0

    return [
        (margin + (lon - min_lon) * scale, height - margin - (lat - min_lat) * scale)
        for lat, lon in points
    ]


def compute_render_size(points: Iterable[tuple[float, float]], max_width: int = 1100, max_height: int = 760, min_width: int = 300, min_height: int = 200) -> tuple[int, int]:
    points = list(points)
    if not points:
        return (max_width, max_height)

    min_lat = min(lat for lat, _ in points)
    max_lat = max(lat for lat, _ in points)
    min_lon = min(lon for _, lon in points)
    max_lon = max(lon for _, lon in points)
    span_lat = max(max_lat - min_lat, 1e-6)
    span_lon = max(max_lon - min_lon, 1e-6)
    margin = 60
    scale = min((max_width - 2 * margin) / span_lon, (max_height - 2 * margin) / span_lat)
    width = max(min_width, min(max_width, int(round(span_lon * scale + 2 * margin))))
    height = max(min_height, min(max_height, int(round(span_lat * scale + 2 * margin))))
    return (max(1, width), max(1, height))


def render_gpx_track(points: Iterable[tuple[float, float]], size: tuple[int, int] | None = None) -> Image.Image:
    points = list(points)
    size = size or compute_render_size(points)
    if not points:
        return Image.new("RGBA", size, (0, 0, 0, 0))

    width, height = size
    render_size = (max(width * 2, 1), max(height * 2, 1))
    map_canvas = Image.new("RGBA", render_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(map_canvas)
    track = project_gpx_points(points, render_size[0], render_size[1], margin=60)
    if len(track) > 1:
        draw.line(track, fill=(0, 0, 0, 255), width=28)
        draw.line(track, fill=(255, 255, 255, 255), width=16)
        draw.line(track, fill=(18, 140, 120, 255), width=8)

    for x, y in track[:1] + track[-1:]:
        draw.ellipse((x - 18, y - 18, x + 18, y + 18), fill=(0, 0, 0, 255))
        draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(255, 255, 255, 255))

    blurred = map_canvas.filter(ImageFilter.GaussianBlur(radius=0.8))
    return blurred.resize(size, Image.Resampling.LANCZOS)


def save_summary_text(gpx_path: str | Path | None, output_path: str | Path) -> Path:
    target = Path(output_path)
    summary = parse_gpx_activity(gpx_path)
    text = "\n".join([
        "Ride summary",
        f"Distance: {summary['distance_km']} km",
        f"Climbing: {summary['climbing_m']} m",
        f"Time: {summary['duration_text']}",
        f"Date: {summary['date']}",
    ]) + "\n"
    target.write_text(text, encoding="utf-8")
    return target


def _parse_exif_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="ignore")
        except Exception:
            return None
    if not isinstance(value, str):
        value = str(value)
    text = value.strip()
    if not text:
        return None

    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass

    for fmt in (
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y:%m:%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S%z",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _extract_track_points_with_times(gpx_path: str | Path | None) -> list[tuple[float, float, datetime]]:
    if gpx_path is None:
        return []

    path = Path(gpx_path)
    if not path.exists():
        return []

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []

    points: list[tuple[float, float, datetime]] = []
    for element in root.iter():
        if not element.tag.endswith("trkpt"):
            continue
        lat = element.attrib.get("lat")
        lon = element.attrib.get("lon")
        if lat is None or lon is None:
            continue

        time_value = ""
        for child in list(element):
            if child.tag.endswith("time"):
                time_value = (child.text or "").strip()
                break
        if not time_value:
            continue

        parsed = _parse_exif_datetime(time_value)
        if parsed is None:
            continue
        try:
            points.append((float(lat), float(lon), parsed))
        except ValueError:
            continue
    return points


def _normalize_datetime(value: datetime, timezone_offset_hours: int = 0) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    if timezone_offset_hours:
        aware_value = value.replace(tzinfo=timezone(timedelta(hours=timezone_offset_hours)))
        return aware_value.astimezone(timezone.utc).replace(tzinfo=None)

    return value


def _infer_local_timezone_offset(track_points: list[tuple[float, float, datetime]], timestamps: list[datetime]) -> int:
    if not timestamps:
        return 0

    track_time_values = [_normalize_datetime(point[2]) for point in track_points]
    best_offset = 0
    best_score = (-1, float("inf"))

    for offset in range(-12, 14):
        matched_count = 0
        total_delta = 0.0
        for timestamp in timestamps:
            candidate = _normalize_datetime(timestamp, offset) if timestamp.tzinfo is None else _normalize_datetime(timestamp)
            nearest = min(track_time_values, key=lambda item: abs((item - candidate).total_seconds()))
            delta = abs((nearest - candidate).total_seconds())
            if delta <= 3600:
                matched_count += 1
                total_delta += delta

        score = (matched_count, -total_delta)
        if score > best_score:
            best_score = score
            best_offset = offset

    return best_offset


def _find_photo_track_positions(folder: str | Path | None, track_points: list[tuple[float, float, datetime]]) -> list[tuple[float, float]]:
    markers = _find_photo_track_markers(folder, track_points)
    return [(marker["lat"], marker["lon"]) for marker in markers]


def _find_photo_track_markers(
    folder: str | Path | None,
    track_points: list[tuple[float, float, datetime]],
    *,
    exclude_paths: set[str | Path] | None = None,
) -> list[dict]:
    if not track_points:
        return []

    directory = Path(folder) if folder is not None else None
    if directory is None or not directory.exists() or not directory.is_dir():
        return []

    excluded = {Path(path).resolve() for path in (exclude_paths or set())}
    photo_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
    photo_timestamps: list[tuple[Path, datetime]] = []

    for path in sorted(directory.iterdir()):
        if path.resolve() in excluded:
            continue
        if "_heatmap" in path.stem.lower() or "_track" in path.stem.lower():
            continue
        if not path.is_file() or path.suffix.lower() not in photo_extensions:
            continue

        timestamp = None
        try:
            with Image.open(path) as image:
                exif = image.getexif()
                if exif:
                    for tag in (36867, 306, 36868):
                        value = exif.get(tag)
                        parsed = _parse_exif_datetime(value)
                        if parsed is not None:
                            timestamp = parsed
                            break
        except Exception:
            pass

        if timestamp is None:
            try:
                timestamp = datetime.fromtimestamp(path.stat().st_mtime)
            except OSError:
                continue

        photo_timestamps.append((path, timestamp))

    if not photo_timestamps:
        return []

    inferred_offset = _infer_local_timezone_offset(track_points, [timestamp for _, timestamp in photo_timestamps])
    markers: list[dict] = []
    for path, timestamp in photo_timestamps:
        normalized_timestamp = _normalize_datetime(timestamp, inferred_offset) if timestamp.tzinfo is None else _normalize_datetime(timestamp)
        nearest = min(
            track_points,
            key=lambda item: abs((_normalize_datetime(item[2]) - normalized_timestamp).total_seconds())
        )
        markers.append({"lat": nearest[0], "lon": nearest[1], "path": path})

    return markers


def _track_projection_context(points: list[tuple[float, float]]) -> dict:
    if not points:
        return {"zoom": 19, "x_tile_min": 0, "y_tile_min": 0, "crop_left": 0, "crop_top": 0, "crop_right": 0, "crop_bottom": 0}

    lat_lon_data = np.asarray(points, dtype=float)
    lat_min = float(np.min(lat_lon_data[:, 0]))
    lon_min = float(np.min(lat_lon_data[:, 1]))
    lat_max = float(np.max(lat_lon_data[:, 0]))
    lon_max = float(np.max(lat_lon_data[:, 1]))

    def deg2xy(lat_deg: float, lon_deg: float, zoom_value: int):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom_value
        x = (lon_deg + 180.0) / 360.0 * n
        y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
        return x, y

    zoom = 19
    while True:
        x_tile_min, y_tile_max = map(int, deg2xy(lat_min, lon_min, zoom))
        x_tile_max, y_tile_min = map(int, deg2xy(lat_max, lon_max, zoom))
        if ((x_tile_max - x_tile_min + 1) * 256 <= 2160 and (y_tile_max - y_tile_min + 1) * 256 <= 3840):
            break
        zoom -= 1

    xy_data = np.array([deg2xy(lat, lon, zoom) for lat, lon in points], dtype=float)
    xy_data = np.round((xy_data - np.array([x_tile_min, y_tile_min], dtype=float)) * 256.0)
    ij_data = np.flip(xy_data.astype(int), axis=1)

    i_min, j_min = np.min(ij_data, axis=0)
    i_max, j_max = np.max(ij_data, axis=0)
    crop_left = max(int(j_min) - 32, 0)
    crop_top = max(int(i_min) - 32, 0)
    crop_right = min(int(j_max) + 32, (x_tile_max - x_tile_min + 1) * 256)
    crop_bottom = min(int(i_max) + 32, (y_tile_max - y_tile_min + 1) * 256)

    return {
        "zoom": zoom,
        "x_tile_min": x_tile_min,
        "y_tile_min": y_tile_min,
        "crop_left": crop_left,
        "crop_top": crop_top,
        "crop_right": crop_right,
        "crop_bottom": crop_bottom,
    }


def _compute_heatmap_crop_for_points(points: list[tuple[float, float]]) -> tuple[int, int, int, int]:
    context = _track_projection_context(points)
    return (context["crop_left"], context["crop_top"], context["crop_right"], context["crop_bottom"])


def _project_latlon_to_image(lat: float, lon: float, image_size: tuple[int, int], points: list[tuple[float, float]]) -> tuple[float, float]:
    if not points:
        return (0.0, 0.0)

    context = _track_projection_context(points)
    width = max(1, image_size[0])
    height = max(1, image_size[1])

    def deg2xy(lat_deg: float, lon_deg: float, zoom_value: int):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom_value
        x = (lon_deg + 180.0) / 360.0 * n
        y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
        return x, y

    x_tile, y_tile = deg2xy(lat, lon, context["zoom"])
    x_pixel = (x_tile - context["x_tile_min"]) * 256.0 - context["crop_left"]
    y_pixel = (y_tile - context["y_tile_min"]) * 256.0 - context["crop_top"]
    x_pixel = max(0.0, min(float(width - 1), x_pixel))
    y_pixel = max(0.0, min(float(height - 1), y_pixel))

    return (float(x_pixel), float(y_pixel))


def _offset_start_end_markers(start_xy: tuple[float, float], end_xy: tuple[float, float], image_size: tuple[int, int]) -> tuple[tuple[float, float], tuple[float, float]]:
    x1, y1 = start_xy
    x2, y2 = end_xy

    start = (max(0.0, min(image_size[0] - 1, x1)), max(0.0, min(image_size[1] - 1, y1)))
    end = (max(0.0, min(image_size[0] - 1, x2)), max(0.0, min(image_size[1] - 1, y2)))

    if math.hypot(end[0] - start[0], end[1] - start[1]) < 14:
        pad = 18
        if end[0] > start[0]:
            end = (end[0] + pad, end[1])
        else:
            end = (end[0] - pad, end[1])
        if end[0] < 0:
            end = (0.0, end[1])
        elif end[0] >= image_size[0]:
            end = (float(image_size[0] - 1), end[1])

    return start, end


def _draw_start_marker(draw: ImageDraw.ImageDraw, center: tuple[float, float]) -> None:
    x, y = center
    radius = 11
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(70, 215, 105), outline=(16, 82, 36), width=3)
    draw.ellipse((x - radius * 0.45, y - radius * 0.45, x + radius * 0.45, y + radius * 0.45), fill=(255, 255, 255), outline=(16, 82, 36), width=2)


def _draw_finish_flag_marker(draw: ImageDraw.ImageDraw, center: tuple[float, float]) -> None:
    x, y = center
    radius = 11
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    for index in range(4):
        start_angle = 45 + index * 90
        end_angle = start_angle + 45
        draw.pieslice((x - radius, y - radius, x + radius, y + radius), start_angle, end_angle, fill=(0, 0, 0))
    draw.line((x + radius + 4, y - radius - 4, x + radius + 4, y + radius + 4), fill=(0, 0, 0), width=2)


def _draw_camera_marker(draw: ImageDraw.ImageDraw, center: tuple[float, float]) -> None:
    x, y = center
    draw.rounded_rectangle((x - 7, y - 5, x + 7, y + 5), radius=2, fill=(252, 150, 63), outline=(30, 30, 30), width=2)
    draw.ellipse((x - 3.5, y - 3.5, x + 3.5, y + 3.5), fill=(255, 255, 255), outline=(30, 30, 30), width=1)
    draw.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill=(30, 30, 30))


def _draw_cluster_connector(draw: ImageDraw.ImageDraw, anchor: tuple[float, float], target: tuple[float, float]) -> None:
    x1, y1 = anchor
    x2, y2 = target
    draw.line((x1, y1, x2, y2), fill=(30, 30, 30, 220), width=2)
    draw.line((x1, y1, x2, y2), fill=(255, 255, 255, 120), width=2)


def _is_in_exclusion_zone(point: tuple[float, float], start_xy: tuple[float, float], end_xy: tuple[float, float], image_size: tuple[int, int]) -> bool:
    threshold = max(18.0, image_size[1] * 0.05)
    for center in (start_xy, end_xy):
        if math.hypot(point[0] - center[0], point[1] - center[1]) <= threshold:
            return True
    return False


def _distance_to_segment(point_x: float, point_y: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(point_x - x1, point_y - y1)
    projection = ((point_x - x1) * dx + (point_y - y1) * dy) / (dx * dx + dy * dy)
    projection = max(0.0, min(1.0, projection))
    px = x1 + projection * dx
    py = y1 + projection * dy
    return math.hypot(point_x - px, point_y - py)


def _box_overlaps_track(box: tuple[int, int, int, int], track_points: list[tuple[float, float]], margin: float = 12.0) -> bool:
    if not track_points or len(track_points) < 2:
        return False

    left, top, right, bottom = box
    cx = (left + right) / 2.0
    cy = (top + bottom) / 2.0
    corners = [
        (left, top),
        (right, top),
        (left, bottom),
        (right, bottom),
        (cx, cy),
    ]

    step_size = max(1, len(track_points) // 8)
    sampled = track_points[::step_size]
    if not sampled:
        sampled = track_points

    for start, end in zip(sampled, sampled[1:]):
        x1, y1 = start
        x2, y2 = end
        min_distance = min(
            _distance_to_segment(px, py, x1, y1, x2, y2)
            for px, py in corners
        )
        if min_distance <= margin + max((right - left), (bottom - top)) * 0.25:
            return True
    return False


def _box_has_track_underneath(box: tuple[int, int, int, int], track_points: list[tuple[float, float]], margin: float = 12.0) -> bool:
    if not track_points or len(track_points) < 2:
        return False

    left, top, right, bottom = box
    xs = [left, (left + right) / 2.0, right]
    ys = [top, (top + bottom) / 2.0, bottom]
    probe_points = []
    for x in xs:
        for y in ys:
            probe_points.append((x, y))
    for x in range(int(left), int(right) + 1, max(4, int((right - left) / 4))):
        for y in range(int(top), int(bottom) + 1, max(4, int((bottom - top) / 4))):
            probe_points.append((float(x), float(y)))

    step_size = max(1, len(track_points) // 12)
    sampled = track_points[::step_size]
    if not sampled:
        sampled = track_points

    for start, end in zip(sampled, sampled[1:]):
        x1, y1 = start
        x2, y2 = end
        if any(_distance_to_segment(px, py, x1, y1, x2, y2) <= margin for px, py in probe_points):
            return True
    return False


def _expand_box(box: tuple[int, int, int, int], padding: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    return (left - padding, top - padding, right + padding, bottom + padding)


def _box_overlap_ratio(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> float:
    left = max(box_a[0], box_b[0])
    top = max(box_a[1], box_b[1])
    right = min(box_a[2], box_b[2])
    bottom = min(box_a[3], box_b[3])
    if right <= left or bottom <= top:
        return 0.0
    overlap_area = (right - left) * (bottom - top)
    area_a = max(1, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
    area_b = max(1, (box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))
    threshold_area = min(area_a, area_b)
    return overlap_area / threshold_area if threshold_area else 0.0


def _compute_non_overlapping_preview_boxes(
    camera_points: list[tuple[float, float]],
    *,
    thumb_size: int,
    image_size: tuple[int, int],
    gap: int = 24,
    existing: list[tuple[int, int, int, int]] | None = None,
    track_points: list[tuple[float, float]] | None = None,
    start_xy: tuple[float, float] | None = None,
    end_xy: tuple[float, float] | None = None,
) -> list[tuple[int, int, int, int]]:
    placed = list(existing or [])
    boxes: list[tuple[int, int, int, int]] = []

    def overlaps(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> bool:
        return not (box_a[2] <= box_b[0] or box_a[0] >= box_b[2] or box_a[3] <= box_b[1] or box_a[1] >= box_b[3])

    def is_valid_box(box: tuple[int, int, int, int]) -> bool:
        padding = 4
        padded_box = _expand_box(box, padding)
        if padded_box[0] < 0 or padded_box[1] < 0 or padded_box[2] > image_size[0] or padded_box[3] > image_size[1]:
            return False

        box_center_x = (box[0] + box[2]) / 2.0
        box_center_y = (box[1] + box[3]) / 2.0
        min_camera_gap = max(26.0, thumb_size * 0.9)
        if math.hypot(box_center_x - center[0], box_center_y - center[1]) < min_camera_gap:
            return False

        for other in placed:
            other_center_x = (other[0] + other[2]) / 2.0
            other_center_y = (other[1] + other[3]) / 2.0
            if math.hypot(box_center_x - other_center_x, box_center_y - other_center_y) < max(12.0, thumb_size * 0.35):
                pass
            if overlaps(padded_box, other):
                ratio = _box_overlap_ratio(padded_box, other)
                if ratio > 0.5:
                    return False

        if track_points is not None:
            track_margin = max(18.0, thumb_size * 0.7 + padding)
            if _box_overlaps_track(padded_box, track_points, margin=track_margin):
                return False
            if _box_has_track_underneath(box, track_points, margin=track_margin):
                return False
        if start_xy is not None and math.hypot((box[0] + box[2]) / 2.0 - start_xy[0], (box[1] + box[3]) / 2.0 - start_xy[1]) <= max(28.0, thumb_size * 1.1 + padding):
            return False
        if end_xy is not None and math.hypot((box[0] + box[2]) / 2.0 - end_xy[0], (box[1] + box[3]) / 2.0 - end_xy[1]) <= max(28.0, thumb_size * 1.1 + padding):
            return False
        return True

    for center in camera_points:
        cx, cy = center
        candidate = None
        radius_step = max(6, int(round(min(image_size) * 0.015)))
        max_radius = max(1, int(round(min(image_size) * 0.42)))
        candidate_positions: list[tuple[int, int, int, int]] = []
        for radius in range(0, max_radius + 1, radius_step):
            for index in range(36):
                angle = math.radians(index * (360 / 36))
                dx = int(round(math.cos(angle) * radius))
                dy = int(round(math.sin(angle) * radius))
                offset = max(20, int(round(thumb_size * 0.9)))
                left = int(round(cx + dx - thumb_size / 2))
                top = int(round(cy + dy - thumb_size / 2 - offset))
                right = left + thumb_size
                bottom = top + thumb_size
                candidate_positions.append((left, top, right, bottom))

        for box in candidate_positions:
            if is_valid_box(box):
                candidate = box
                break

        if candidate is None:
            continue
        placed.append(candidate)
        boxes.append(candidate)

    return boxes


PHOTO_LAYOUT_CACHE_VERSION = 2
PHOTO_LAYOUT_CACHE_RUN_ID = uuid.uuid4().hex


def _photo_layout_cache_path(image_path: str | Path) -> Path:
    return Path(image_path).parent / ".photo_preview_layout_cache.json"


def _render_cache_key(image_path: str | Path, image_size: tuple[int, int], *, render_variant: str = "default") -> str:
    return f"{PHOTO_LAYOUT_CACHE_RUN_ID}:{render_variant}:{Path(image_path).resolve()}::{image_size[0]}x{image_size[1]}"


def _photo_signature(path: str | Path) -> tuple[str, int, int]:
    resolved = Path(path).resolve()
    try:
        stat = resolved.stat()
        return (str(resolved), int(stat.st_mtime_ns), int(stat.st_size))
    except OSError:
        return (str(resolved), 0, 0)


def _load_photo_layout_cache(image_path: str | Path, image_size: tuple[int, int], *, render_variant: str = "default") -> dict[str, dict]:
    cache_path = _photo_layout_cache_path(image_path)
    if not cache_path.exists():
        return {}

    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}
    if data.get("cache_version") != PHOTO_LAYOUT_CACHE_VERSION:
        return {}
    if data.get("image_size") != [image_size[0], image_size[1]]:
        return {}

    cache_key = _render_cache_key(image_path, image_size, render_variant=render_variant)
    entries = data.get("entries", {})
    if not isinstance(entries, dict):
        return {}
    reuse_entries = entries.get(cache_key, {})
    return reuse_entries if isinstance(reuse_entries, dict) else {}


def _save_photo_layout_cache(image_path: str | Path, image_size: tuple[int, int], entries: dict[str, dict], *, render_variant: str = "default") -> None:
    cache_path = _photo_layout_cache_path(image_path)
    cache_key = _render_cache_key(image_path, image_size, render_variant=render_variant)
    try:
        existing = {}
        if cache_path.exists():
            try:
                existing = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        if not isinstance(existing, dict):
            existing = {}
        existing["cache_version"] = PHOTO_LAYOUT_CACHE_VERSION
        existing["image_size"] = [image_size[0], image_size[1]]
        rendered_entries = existing.get("entries", {}) if isinstance(existing.get("entries", {}), dict) else {}
        rendered_entries = {k: v for k, v in rendered_entries.items() if k.startswith(f"{PHOTO_LAYOUT_CACHE_RUN_ID}:")}
        rendered_entries[cache_key] = entries
        existing["entries"] = rendered_entries
        cache_path.write_text(json.dumps(existing, sort_keys=True), encoding="utf-8")
    except Exception:
        return


def _build_photo_frame(photo: Image.Image, thumb_size: int, padding: int = 3) -> Image.Image:
    image = photo.convert("RGBA")
    crop_size = min(image.width, image.height)
    square_crop = ImageOps.fit(image, (crop_size, crop_size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    resized = square_crop.resize((thumb_size, thumb_size), Image.Resampling.LANCZOS)

    frame = Image.new("RGBA", (thumb_size + 2 * padding, thumb_size + 2 * padding), (0, 0, 0, 0))
    frame.paste(resized, (padding, padding), resized)
    ImageDraw.Draw(frame).rectangle((0, 0, frame.width - 1, frame.height - 1), outline=(255, 255, 255, 160), width=1)
    return frame


def _annotate_heatmap_with_track_markers(image_path: str | Path, points: list[tuple[float, float]], photo_markers: list[dict], *, render_variant: str = "default") -> None:
    if not points:
        return

    path = Path(image_path)
    if not path.exists():
        return

    print(f"[photo] evaluating {len(photo_markers)} image markers for {path.name}")

    try:
        with Image.open(path) as image:
            overlay = image.convert("RGBA")
            draw = ImageDraw.Draw(overlay)

            start_xy = _project_latlon_to_image(points[0][0], points[0][1], overlay.size, points)
            end_xy = _project_latlon_to_image(points[-1][0], points[-1][1], overlay.size, points)
            start_xy, end_xy = _offset_start_end_markers(start_xy, end_xy, overlay.size)
            _draw_finish_flag_marker(draw, end_xy)
            _draw_start_marker(draw, start_xy)

            projected_markers = []
            for marker in photo_markers:
                lat = float(marker["lat"])
                lon = float(marker["lon"])
                projected_markers.append({
                    "marker": marker,
                    "xy": _project_latlon_to_image(lat, lon, overlay.size, points),
                })

            valid_markers = [entry for entry in projected_markers if not _is_in_exclusion_zone(entry["xy"], start_xy, end_xy, overlay.size)]
            print(f"[photo] {len(valid_markers)} valid markers remain after exclusion checks")
            cache_entries = _load_photo_layout_cache(path, overlay.size, render_variant=render_variant)
            cache_ready = bool(cache_entries)
            for entry in valid_markers:
                marker_path = Path(entry["marker"]["path"])
                key = str(marker_path.resolve())
                if key not in cache_entries:
                    cache_ready = False
                    break
                signature = _photo_signature(marker_path)
                cached_signature = cache_entries[key].get("signature")
                if cached_signature != list(signature):
                    cache_ready = False
                    break

            if cache_ready:
                pending_thumbs: list[tuple[Path, tuple[int, int, int, int], int, int]] = []
                for entry in valid_markers:
                    marker_path = Path(entry["marker"]["path"])
                    key = str(marker_path.resolve())
                    cached = cache_entries[key]
                    preview_box = tuple(cached["box"])
                    thumb_size = int(cached["thumb_size"])
                    padding = 3
                    preview_anchor = (
                        float(preview_box[0] + (thumb_size + 2 * padding) / 2),
                        float(preview_box[1] + (thumb_size + 2 * padding)),
                    )
                    _draw_cluster_connector(draw, preview_anchor, entry["xy"])
                    _draw_camera_marker(draw, entry["xy"])
                    pending_thumbs.append((marker_path, preview_box, thumb_size, padding))

                for marker_path, preview_box, thumb_size, padding in pending_thumbs:
                    try:
                        with Image.open(marker_path) as photo:
                            frame = _build_photo_frame(photo, thumb_size, padding=padding)
                            overlay.paste(frame, (preview_box[0], preview_box[1]), frame)
                    except Exception:
                        pass
                overlay.save(path)
                return

            track_pixels = [
                _project_latlon_to_image(float(lat), float(lon), overlay.size, points)
                for lat, lon, *_ in points
            ]
            placed_preview_boxes: list[tuple[int, int, int, int]] = []
            next_cache_entries: dict[str, dict] = {}
            pending_thumbs: list[tuple[Path, tuple[int, int, int, int], int, int]] = []

            for index, entry in enumerate(valid_markers, start=1):
                camera_xy = entry["xy"]
                print(f"[photo] placing preview {index}/{len(valid_markers)}")
                nearest_distance = min(
                    (math.hypot(camera_xy[0] - other["xy"][0], camera_xy[1] - other["xy"][1]) for other in valid_markers if other is not entry),
                    default=float("inf"),
                )
                is_clustered = nearest_distance <= overlay.height * 0.08
                ratio = 0.10 if is_clustered else 0.15
                thumb_side = max(32, int(round(overlay.height * ratio)))
                thumb_side = min(thumb_side, 150)
                gap = 22 if is_clustered else 30

                preview_boxes = _compute_non_overlapping_preview_boxes(
                    [camera_xy],
                    thumb_size=thumb_side,
                    image_size=overlay.size,
                    gap=gap,
                    existing=placed_preview_boxes,
                    track_points=track_pixels,
                    start_xy=start_xy,
                    end_xy=end_xy,
                )
                if not preview_boxes:
                    continue

                preview_box = preview_boxes[0]
                padding = 3
                frame_box = _expand_box(preview_box, padding)
                marker_path = Path(entry["marker"]["path"])
                key = str(marker_path.resolve())
                next_cache_entries[key] = {
                    "signature": list(_photo_signature(marker_path)),
                    "thumb_size": thumb_side,
                    "box": [int(frame_box[0]), int(frame_box[1]), int(frame_box[2]), int(frame_box[3])],
                }
                preview_anchor = (
                    float(frame_box[0] + (thumb_side + 2 * padding) / 2),
                    float(frame_box[1] + (thumb_side + 2 * padding)),
                )
                _draw_cluster_connector(draw, preview_anchor, entry["xy"])
                _draw_camera_marker(draw, entry["xy"])
                pending_thumbs.append((marker_path, frame_box, thumb_side, padding))
                placed_preview_boxes.append(frame_box)

            for marker_path, preview_box, thumb_size, padding in pending_thumbs:
                try:
                    with Image.open(marker_path) as photo:
                        frame = _build_photo_frame(photo, thumb_size, padding=padding)
                        overlay.paste(frame, (preview_box[0], preview_box[1]), frame)
                except Exception:
                    pass

            _save_photo_layout_cache(path, overlay.size, next_cache_entries, render_variant=render_variant)
            overlay.save(path)
    except Exception:
        return


def pick_gpx_file(folder: str | Path | None = None) -> Path | None:
    directory = Path(folder) if folder is not None else Path.cwd()
    if not directory.exists():
        return None

    gpx_files = sorted(
        path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".gpx"
    )
    if not gpx_files:
        return None
    if len(gpx_files) == 1:
        return gpx_files[0]

    print("Multiple GPX files found in the current directory:")
    for index, path in enumerate(gpx_files, start=1):
        print(f"  {index}. {path.name}")

    while True:
        choice = input("Select a GPX file by number: ").strip()
        try:
            selected_index = int(choice)
        except ValueError:
            print("Please enter a valid number.")
            continue
        if 1 <= selected_index <= len(gpx_files):
            return gpx_files[selected_index - 1]
        print(f"Please choose a number between 1 and {len(gpx_files)}.")


def render_gpx_heatmap(
    gpx_path: str | Path,
    output_path: str | Path | None = None,
    *,
    zoom: int = -1,
    sigma: int = 1,
    orange: bool = False,
    natural: bool = False,
    csv: bool = False,
    include_photo_markers: bool = True,
) -> Path:
    source = Path(gpx_path)
    if not source.exists():
        raise FileNotFoundError(f"GPX file does not exist: {source}")

    points = extract_gpx_points(source)
    if not points:
        raise ValueError(f"No track points found in GPX file: {source}")

    latitudes = [lat for lat, _ in points]
    longitudes = [lon for _, lon in points]
    bounds = (min(latitudes), max(latitudes), min(longitudes), max(longitudes))

    target = _sanitize_output_path(output_path) if output_path is not None else _sanitize_output_path(source.with_name(f"{source.stem}_heatmap.png"))
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"[render] generating heatmap for {source.name} -> {target.name}")

    heatmap_func = generate_heatmap_from_points
    if heatmap_func is None:
        heatmap_module = _load_strava_heatmap_module()
        heatmap_func = heatmap_module.generate_heatmap_from_points

    args = argparse.Namespace(
        bounds=bounds,
        zoom=zoom,
        sigma=sigma,
        orange=orange,
        natural=natural,
        single_track=natural,
        csv=csv,
        use_local_dir=True,
        output=str(target),
        dir=str(source.parent),
        filter="*.gpx",
        year=[],
        cluster_min_size=2,
        html=False,
    )

    heatmap_func(
        np.asarray(points, dtype=float),
        str(target),
        args,
        gpx_files_count=1,
        bounds=bounds,
    )

    if include_photo_markers or natural:
        print(f"[render] adding annotations for {target.name}")
        track_points_with_times = _extract_track_points_with_times(source)
        photo_markers = _find_photo_track_markers(source.parent, track_points_with_times, exclude_paths={target.resolve()}) if include_photo_markers else []
        _annotate_heatmap_with_track_markers(target, points, photo_markers, render_variant="natural" if natural else "standard")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the GPX tile heatmap.")
    parser.add_argument("gpx_path", nargs="?", default=None, help="Path to the GPX file to render.")
    parser.add_argument("--output-dir", dest="output_dir", help="Directory to write the generated heatmap to.")
    parser.add_argument("--zoom", type=int, default=-1, help="Zoom level for the tile-based heatmap generation.")
    parser.add_argument("--sigma", type=int, default=1, help="Gaussian sigma for the tile-based heatmap generation.")
    parser.add_argument("--natural", action="store_true", help="Render the natural OSM-like heatmap instead of the original monochrome variant.")
    args = parser.parse_args()

    source = Path(args.gpx_path) if args.gpx_path else pick_gpx_file(Path.cwd())
    if source is None:
        raise FileNotFoundError("No GPX file found in the current directory.")

    output_dir = Path(args.output_dir) if args.output_dir else source.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    standard_path = _sanitize_output_path(output_dir / f"{source.stem}_heatmap_standard.png")
    standard_no_images_path = _sanitize_output_path(output_dir / f"{source.stem}_heatmap_standard_no_images.png")
    natural_path = _sanitize_output_path(output_dir / f"{source.stem}_heatmap_natural.png")
    natural_no_images_path = _sanitize_output_path(output_dir / f"{source.stem}_heatmap_natural_no_images.png")

    render_gpx_heatmap(source, standard_path, zoom=args.zoom, sigma=args.sigma, natural=False, include_photo_markers=True)
    render_gpx_heatmap(source, standard_no_images_path, zoom=args.zoom, sigma=args.sigma, natural=False, include_photo_markers=False)
    render_gpx_heatmap(source, natural_path, zoom=args.zoom, sigma=args.sigma, natural=True, include_photo_markers=True)
    render_gpx_heatmap(source, natural_no_images_path, zoom=args.zoom, sigma=args.sigma, natural=True, include_photo_markers=False)

    print(f"Saved standard heatmap: {standard_path}")
    print(f"Saved standard no-photo heatmap: {standard_no_images_path}")
    print(f"Saved natural heatmap: {natural_path}")
    print(f"Saved natural no-photo heatmap: {natural_no_images_path}")


if __name__ == "__main__":
    main()
