from __future__ import annotations

import argparse
import importlib.util
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


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


def _find_photo_track_markers(folder: str | Path | None, track_points: list[tuple[float, float, datetime]]) -> list[dict]:
    if not track_points:
        return []

    directory = Path(folder) if folder is not None else None
    if directory is None or not directory.exists() or not directory.is_dir():
        return []

    photo_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
    photo_timestamps: list[tuple[Path, datetime]] = []

    for path in sorted(directory.iterdir()):
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
    radius = 5
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


def _is_in_exclusion_zone(point: tuple[float, float], start_xy: tuple[float, float], end_xy: tuple[float, float], image_size: tuple[int, int]) -> bool:
    threshold = max(18.0, image_size[1] * 0.05)
    for center in (start_xy, end_xy):
        if math.hypot(point[0] - center[0], point[1] - center[1]) <= threshold:
            return True
    return False


def _compute_non_overlapping_preview_boxes(
    camera_points: list[tuple[float, float]],
    *,
    thumb_size: int,
    image_size: tuple[int, int],
    gap: int = 24,
    existing: list[tuple[int, int, int, int]] | None = None,
) -> list[tuple[int, int, int, int]]:
    placed = list(existing or [])
    boxes: list[tuple[int, int, int, int]] = []

    def overlaps(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> bool:
        return not (box_a[2] <= box_b[0] or box_a[0] >= box_b[2] or box_a[3] <= box_b[1] or box_a[1] >= box_b[3])

    for center in camera_points:
        cx, cy = center
        step = max(12, thumb_size // 2)
        candidate = None
        for distance in range(0, 220, step):
            for angle in range(0, 360, 45):
                dx = round(math.cos(math.radians(angle)) * distance)
                dy = round(math.sin(math.radians(angle)) * distance)
                left = int(cx - thumb_size / 2 + dx)
                top = int(cy - thumb_size - gap + dy)
                right = left + thumb_size
                bottom = top + thumb_size
                if left < 0 or top < 0 or right > image_size[0] or bottom > image_size[1]:
                    continue
                box = (left, top, right, bottom)
                if any(overlaps(box, other) for other in placed):
                    continue
                candidate = box
                break
            if candidate is not None:
                break

        if candidate is None:
            continue
        placed.append(candidate)
        boxes.append(candidate)

    return boxes


def _annotate_heatmap_with_track_markers(image_path: str | Path, points: list[tuple[float, float]], photo_markers: list[dict]) -> None:
    if not points:
        return

    path = Path(image_path)
    if not path.exists():
        return

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

            placed_preview_boxes: list[tuple[int, int, int, int]] = []
            for entry in projected_markers:
                marker = entry["marker"]
                camera_xy = entry["xy"]
                if _is_in_exclusion_zone(camera_xy, start_xy, end_xy, overlay.size):
                    continue

                other_points = [
                    other["xy"]
                    for other in projected_markers
                    if other is not entry and not _is_in_exclusion_zone(other["xy"], start_xy, end_xy, overlay.size)
                ]
                nearest_distance = min(
                    (math.hypot(camera_xy[0] - other[0], camera_xy[1] - other[1]) for other in other_points),
                    default=float("inf"),
                )
                is_clustered = nearest_distance <= overlay.height * 0.18
                ratio = 0.10 if is_clustered else 0.15
                thumb_side = max(32, int(round(overlay.height * ratio)))
                thumb_side = min(thumb_side, 150)
                gap = 24 if is_clustered else 30

                photo_path = marker["path"]
                try:
                    with Image.open(photo_path) as photo:
                        thumb = photo.convert("RGBA")
                        thumb = thumb.resize((thumb_side, thumb_side), Image.Resampling.LANCZOS)
                        preview_boxes = _compute_non_overlapping_preview_boxes(
                            [camera_xy],
                            thumb_size=thumb_side,
                            image_size=overlay.size,
                            gap=gap,
                            existing=placed_preview_boxes,
                        )
                        if not preview_boxes:
                            continue
                        preview_box = preview_boxes[0]
                        placed_preview_boxes.append(preview_box)
                        overlay.paste(thumb, (preview_box[0], preview_box[1]), thumb)
                except Exception:
                    pass

                _draw_camera_marker(draw, camera_xy)

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

    target = Path(output_path) if output_path is not None else source.with_name(f"{source.stem}_heatmap.png")
    target.parent.mkdir(parents=True, exist_ok=True)

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

    if include_photo_markers:
        track_points_with_times = _extract_track_points_with_times(source)
        photo_markers = _find_photo_track_markers(source.parent, track_points_with_times)
        _annotate_heatmap_with_track_markers(target, points, photo_markers)
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

    standard_path = output_dir / f"{source.stem}_heatmap_standard.png"
    standard_no_images_path = output_dir / f"{source.stem}_heatmap_standard_no_images.png"
    natural_path = output_dir / f"{source.stem}_heatmap_natural.png"
    natural_no_images_path = output_dir / f"{source.stem}_heatmap_natural_no_images.png"

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
