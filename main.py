import gzip
import html
import json
import os
import re
import shutil
from typing import Any
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path



def esc(value):
    return html.escape(str(value), quote=False)

# 广州市海珠区（琶洲片区所属行政区）官方 Location ID
# 说明：免费套餐不含 GeoAPI/POI 接口，无法精确检索"琶洲"POI，
# 和风天气按坐标反查时自动命中最新区域站点即为海珠区(101280108)。
GUANGZHOU_LOCATION = "101280108"
# 经纬度坐标，供新版预警接口 /weatheralert/v1/current/{lat}/{lon} 使用（经度,纬度）
GUANGZHOU_COORDS = "113.384,23.101"
CITY_NAME = "广州·海珠琶洲"
UMBRELLA_POP_THRESHOLD = 40
RAIN_KEYWORDS = ("雨", "雪", "雹")

TZ = ZoneInfo("Asia/Shanghai")


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"Missing environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def parse_webhook_urls(raw: str) -> list[str]:
    """解析 WECOM_WEBHOOK_URL，支持配置多个企业微信 Webhook。

    多个地址之间用英文逗号、英文分号或换行分隔，例如：
        WECOM_WEBHOOK_URL="https://qyapi.../key=aaa,https://qyapi.../key=bbb"
    自动去除空白项与重复项，保持原有顺序。
    """
    urls = [u.strip() for u in re.split(r"[,;\n]+", raw) if u.strip()]
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls


def http_get_json(url: str, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        encoding = (response.headers.get("Content-Encoding") or "").lower()
        # QWeather may return gzip even when urllib didn't advertise it; also
        # guard against a missing/uppercase header by sniffing the gzip magic bytes.
        if encoding == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def http_post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def qweather_get(host: str, api_key: str, path: str, params: dict | None = None) -> dict[str, Any]:
    query = dict(params or {})
    query["location"] = GUANGZHOU_LOCATION
    url = f"https://{host}{path}?{urllib.parse.urlencode(query)}"
    payload = http_get_json(url, headers={"X-QW-Api-Key": api_key})
    if payload.get("code") != "200":
        raise RuntimeError(f"QWeather API error for {path}: {payload}")
    return payload


def parse_fx_time(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(TZ)


def format_hour(value: str) -> str:
    return parse_fx_time(value).strftime("%H:%M")


def is_rainy_text(text: str) -> bool:
    return any(keyword in text for keyword in RAIN_KEYWORDS)


def pop_value(value: str | int | None) -> int:
    if value in (None, ""):
        return 0
    return int(value)


def parse_wind_scale(s: str) -> int:
    try:
        return max(int(x) for x in s.split("-"))
    except (ValueError, TypeError):
        return 0


def fetch_warnings(host: str, api_key: str) -> list[dict[str, Any]]:
    # 新版预警接口 /weatheralert/v1/current/{lat}/{lon}（含中国及全球预警）。
    # 旧接口 /v7/warning/now 已被官方弃用，且本账户无访问权限（HTTP 403），故迁移至此。
    lon, lat = GUANGZHOU_COORDS.split(",")
    url = f"https://{host}/weatheralert/v1/current/{lat}/{lon}?lang=zh"
    try:
        payload = http_get_json(url, headers={"X-QW-Api-Key": api_key})
    except urllib.error.HTTPError as exc:
        print(f"⚠️  预警接口请求失败（HTTP {exc.code}），跳过")
        return []
    if "alerts" not in payload:
        print("⚠️  预警接口返回异常，跳过")
        return []
    return payload.get("alerts") or []


def fetch_weather(host: str, api_key: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    now = qweather_get(host, api_key, "/v7/weather/now")["now"]
    hourly = qweather_get(host, api_key, "/v7/weather/24h")["hourly"]
    warnings = fetch_warnings(host, api_key)
    # 指数类型：1 运动 3 穿衣 5 紫外线 6 旅游 8 舒适度 9 感冒 11 空调开启
    # 10 空气污染扩散条件 14 晾晒 15 交通 16 防晒
    indices = qweather_get(
        host, api_key, "/v7/indices/1d", {"type": "1,3,5,6,8,9,10,11,14,15,16"}
    ).get("daily", [])
    return now, hourly, warnings, indices


def fetch_3d_forecast(host: str, api_key: str) -> list[dict[str, Any]]:
    # 3 天预报接口（免费，含未来 3 天逐日最高/最低温、白天/夜间天气、降水量等）。
    # 任一异常均优雅降级：返回空列表，不阻断整体推送。
    try:
        return qweather_get(host, api_key, "/v7/weather/3d").get("daily", [])
    except Exception as exc:  # noqa: BLE001 - 网络/接口异常统一降级
        print(f"⚠️  3 天预报接口请求失败（{exc}），跳过")
        return []


def fetch_air_quality(host: str, api_key: str) -> dict[str, Any] | None:
    # 新版全球空气质量接口 /airquality/v1/current/{lat}/{lon}（1×1 km 分辨率）。
    # 旧接口 /v7/airquality/now 已在网关下线（HTTP 404，空 body），故迁移至此，
    # 与 fetch_warnings 的预警接口迁移同理。
    # 响应结构与旧版不同：多标准指数在 indexes[] 数组中，优先取中国标准 cn-mee。
    lon, lat = GUANGZHOU_COORDS.split(",")
    url = f"https://{host}/airquality/v1/current/{lat}/{lon}?lang=zh"
    try:
        payload = http_get_json(url, headers={"X-QW-Api-Key": api_key})
    except Exception as exc:  # noqa: BLE001 - 网络/接口异常统一降级
        print(f"⚠️  空气质量接口请求失败（{exc}），跳过")
        return None
    indexes: list[dict[str, Any]] = payload.get("indexes") or []
    if not indexes:
        print("⚠️  空气质量接口返回异常，跳过")
        return None
    return next((item for item in indexes if item.get("code") == "cn-mee"), indexes[0])


def fetch_astronomy(host: str, api_key: str) -> dict[str, Any]:
    # 天文接口（免费全球）：日出日落 + 月相，按当天日期查询。
    # 注意：date 必须为 YYYYMMDD（无横线）；日出接口路径为 /v7/astronomy/sun。
    # 任一接口失败不影响另一接口，整体缺失时返回空 dict，由 build 函数兜底。
    today = datetime.now(TZ).strftime("%Y%m%d")
    result: dict[str, Any] = {}
    try:
        result["sun"] = qweather_get(host, api_key, "/v7/astronomy/sun", {"date": today})
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  日出日落接口请求失败（{exc}），跳过")
    try:
        result["moon"] = qweather_get(host, api_key, "/v7/astronomy/moon", {"date": today})
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  月相接口请求失败（{exc}），跳过")
    return result


def build_next_6h_lines(hourly: list[dict]) -> list[str]:
    lines = []
    for item in hourly[:6]:
        pop = pop_value(item.get("pop"))
        text = item['text']
        # 雨天/雪天用对应 emoji 标记
        if is_rainy_text(text):
            icon = "🌧️" if "雨" in text else ("❄️" if "雪" in text else "🌨️")
        else:
            icon = "☁️" if "云" in text or "阴" in text else "☀️"
        lines.append(
            f"{icon} `{format_hour(item['fxTime'])}`　{text}　**{item['temp']}°C**　💧降水概率 {pop}%"
        )
    return lines


def build_24h_summary(hourly: list[dict]) -> str:
    temps = [int(item["temp"]) for item in hourly]
    min_temp = min(temps)
    max_temp = max(temps)
    has_rain = any(
        is_rainy_text(item.get("text", "")) or pop_value(item.get("pop")) >= UMBRELLA_POP_THRESHOLD
        for item in hourly
    )

    wind_scales = [parse_wind_scale(item.get("windScale", "0")) for item in hourly if item.get("windScale")]
    if wind_scales:
        wind_summary = f"💨 风力 {min(wind_scales)}-{max(wind_scales)} 级"
    else:
        wind_summary = "💨 风力未知"
    rain_text = "🌧️ 有雨" if has_rain else "☀️ 无雨"
    temp_icon = "🌡️"
    return f"{temp_icon} **{min_temp}°C ~ {max_temp}°C**　|　{rain_text}　|　{wind_summary}"


_WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]


def format_day_label(fx_date: str, index: int) -> str:
    if index == 0:
        return "今天"
    if index == 1:
        return "明天"
    weekday = datetime.fromisoformat(fx_date).weekday()
    return f"周{_WEEKDAY_CN[weekday]}"


def build_3d_forecast_lines(daily: list[dict[str, Any]]) -> str:
    if not daily:
        return "🌫️ 暂无 3 天预报数据"
    lines = []
    for index, item in enumerate(daily):
        text_day = item.get("textDay", "")
        icon = "🌧️" if is_rainy_text(text_day) else ("☁️" if "云" in text_day or "阴" in text_day else "☀️")
        label = format_day_label(item.get("fxDate", ""), index)
        precip = item.get("precip")
        precip_text = f"　💧 {precip}mm" if precip and float(precip) > 0 else ""
        lines.append(
            f"{icon} `{label}`　{text_day}　"
            f"**{item.get('tempMin', '-')}~{item.get('tempMax', '-')}°C**{precip_text}"
        )
    return "\n".join(lines)


_SEVERITY_LABEL = {
    "extreme": "红色",
    "severe": "橙色",
    "moderate": "黄色",
    "minor": "蓝色",
    "unknown": "未知",
}
_COLOR_LABEL = {
    "red": "红色",
    "orange": "橙色",
    "yellow": "黄色",
    "blue": "蓝色",
}


def format_warning_level(item: dict[str, Any]) -> str:
    color = (item.get("color") or {}).get("code", "")
    if color:
        # 仅识别红/橙/黄/蓝四种官方标准预警色；其余颜色码（如"提醒"类预警常见的
        # gray/white 等非定级色）不在色卡内，不应把和风天气返回的原始英文 code
        # 泄露到用户可见文案中，因此 fallback 为空字符串（不展示色块 chip）。
        return _COLOR_LABEL.get(color, "")
    return _SEVERITY_LABEL.get(item.get("severity", ""), "")


def build_warning_lines(warnings: list[dict[str, Any]]) -> list[str]:
    if not warnings:
        return ["✅ 暂无气象预警"]
    lines = []
    for item in warnings:
        title = item.get("headLine") or item.get("headline") or "预警"
        event = (item.get("eventType") or {}).get("name", "")
        level = format_warning_level(item)
        # 预警等级用颜色色块
        level_chip = f" `{level}`" if level else ""
        event_chip = f"【{event}】" if event else ""
        lines.append(f"> ⚠️　{event_chip}**{title}**{level_chip}")
    return lines


def index_by_type(indices: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for item in indices:
        result[item["type"]] = item
    return result


def build_umbrella_advice(hourly: list[dict]) -> str:
    next_6h = hourly[:6]
    for item in next_6h:
        if is_rainy_text(item.get("text", "")) or pop_value(item.get("pop")) >= UMBRELLA_POP_THRESHOLD:
            return "☂️ **建议带伞**（未来 6 小时降水概率偏高或有雨雪）"
    return "😎 **无需带伞**"


_INDEX_ICONS = {
    "带伞": "☂️",
    "空调": "❄️",
    "衣着": "👕",
    "紫外线": "🔆",
    "感冒": "🤧",
    "运动": "🏃",
    "旅游": "🧳",
    "舒适度": "🛋️",
    "晾晒": "👔",
    "防晒": "🧴",
    "交通": "🚗",
    "空气扩散": "🌬️",
}


def format_index_line(name: str, item: dict | None) -> str:
    icon = _INDEX_ICONS.get(name, "•")
    if not item:
        return f"{icon} **{name}**：暂无数据"
    category = item.get("category", "")
    text = item.get("text", "")
    if category and text:
        return f"{icon} **{name}**：`{category}`　{text}"
    if category:
        return f"{icon} **{name}**：`{category}`"
    if text:
        return f"{icon} **{name}**：{text}"
    return f"{icon} **{name}**：暂无数据"


_AQI_ICON = {
    "优": "🌿",
    "良": "😊",
    "轻度污染": "😷",
    "中度污染": "🤢",
    "重度污染": "🤮",
    "严重污染": "☠️",
}


_POLLUTANT_LABEL = {
    "pm2p5": "PM2.5",
    "pm10": "PM10",
    "no2": "NO2",
    "o3": "O3",
    "so2": "SO2",
    "co": "CO",
}


def build_air_quality_lines(aq: dict[str, Any] | None) -> str:
    if not aq:
        return "🌫️ 暂无空气质量数据"
    aqi = aq.get("aqi", "-")
    category = aq.get("category", "")
    # 新版接口字段为 primaryPollutant（污染物代码，如 "pm2p5"），无主要污染物时为 None。
    primary = aq.get("primaryPollutant") or ""
    primary_label = _POLLUTANT_LABEL.get(primary, primary.upper()) if primary else ""
    primary_text = f"　主要污染物 `{primary_label}`" if primary_label else ""
    icon = _AQI_ICON.get(category, "🌫️")
    line = f"{icon} **AQI {aqi}　{category}**{primary_text}"
    # 健康建议：effect 为综合描述（字符串）；advice 为分人群建议（字典），取通用人群建议兜底。
    health: dict[str, Any] = aq.get("health") or {}
    advice_text = health.get("effect") or ""
    if not advice_text:
        advice = health.get("advice")
        if isinstance(advice, dict):
            advice_text = advice.get("generalPopulation") or ""
    if advice_text:
        line += f"\n　　🩺 {advice_text}"
    return line


def build_astronomy_lines(astro: dict[str, Any]) -> str:
    # astro 为 fetch_astronomy 返回的顶层响应（可能含 sun / moon 两段）。
    sun: dict[str, Any] = astro.get("sun") or {}
    moon: dict[str, Any] = astro.get("moon") or {}
    if not sun and not moon:
        return "🌌 暂无天文数据"
    parts: list[str] = []
    if sun:
        rise = format_hour(sun.get("sunrise", "")) if sun.get("sunrise") else ""
        set_ = format_hour(sun.get("sunset", "")) if sun.get("sunset") else ""
        if rise and set_:
            parts.append(f"🌅 日出 {rise} / 日落 {set_}")
    if moon:
        # moonPhase 为按小时数组，取当日第一个有效相位的名称；无数组则退化为顶层字段。
        phase_name = ""
        phase_list: list[dict[str, Any]] = moon.get("moonPhase") or []
        if phase_list:
            phase_name = phase_list[0].get("name", "")
        else:
            phase_name = moon.get("name") or moon.get("phase") or ""
        if phase_name:
            parts.append(f"🌙 月相 {phase_name}")
    return "　".join(parts) if parts else "🌌 暂无天文数据"


def mask_webhook_url(url: str) -> str:
    """日志脱敏：仅保留 Webhook key 首尾少量字符，避免泄露完整密钥。"""
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    key = (query.get("key") or [""])[0]
    if not key:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    masked_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "*" * len(key)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?key={masked_key}"


def truncate_text(text, max_len):
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def weather_emoji(text):
    if "雷" in text:
        return "⛈️"
    if is_rainy_text(text):
        if "雪" in text:
            return "❄️"
        if "雹" in text:
            return "🌨️"
        return "🌧️"
    if "雾" in text or "霾" in text:
        return "🌫️"
    if "云" in text or "阴" in text:
        return "☁️"
    return "☀️"


def build_hourly_vertical(hourly, max_len=112, include_pop: bool = True):
    lines = []
    for item in hourly[:6]:
        fx_time = item.get("fxTime", "")
        if not fx_time:
            continue
        pop = pop_value(item.get("pop"))
        weather_text = item.get("text", "")
        temp = item.get("temp", "-")
        pop_suffix = f" {pop}%" if include_pop and pop else ""
        line = (
            f"🕐{format_hour(fx_time)} {weather_emoji(weather_text)}{weather_text} "
            f"{temp}°C{pop_suffix}"
        )
        lines.append(line)
    return "\n".join(lines)


def build_card_now_lines(now_ctx: dict[str, Any]) -> tuple[str, str]:
    text = now_ctx.get("text", "")
    temp = now_ctx.get("temp", "-")
    feels = now_ctx.get("feels_like", "-")
    humidity = now_ctx.get("humidity", "-")
    wind_dir = now_ctx.get("wind_dir", "")
    wind_scale = now_ctx.get("wind_scale", "")
    emoji = weather_emoji(text)
    line1 = f"{emoji} {text}　{temp}°C　|　🤚 体感 {feels}°C"
    line2 = f"💧 湿度 {humidity}%　|　🌬️ {wind_dir} {wind_scale}级"
    return line1, line2


def build_card_warning_desc(warnings_list: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in warnings_list:
        title = item.get("title", "预警")
        event = item.get("event", "")
        level = item.get("level", "")
        level_part = f"   {level}" if level else ""
        event_part = f"【{event}】" if event else ""
        lines.append(f"⚠️　{event_part}{title}{level_part}")
    return "\n".join(lines)


def build_card_astro_desc(astro: dict[str, Any]) -> str:
    ctx = build_astronomy_context(astro)
    if ctx.get("empty"):
        return ""
    parts: list[str] = []
    sunrise = ctx.get("sunrise", "")
    sunset = ctx.get("sunset", "")
    if sunrise and sunset:
        parts.append(f"🌅 日出 {sunrise} / 日落 {sunset}")
    moon_phase = ctx.get("moon_phase", "")
    if moon_phase:
        parts.append(f"🌙 月相 {moon_phase}")
    return "　".join(parts)


def build_card_vertical_items(
    now_ctx: dict[str, Any],
    hourly: list[dict[str, Any]],
    warnings_list: list[dict[str, Any]],
    astro: dict[str, Any],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if warnings_list:
        items.append(
            {
                "title": "🚨 气象预警",
                "desc": build_card_warning_desc(warnings_list),
            }
        )
    hourly_desc = build_hourly_vertical(hourly, include_pop=False)
    if hourly_desc:
        items.append(
            {
                "title": "⏭️ 未来6小时",
                "desc": hourly_desc,
            }
        )
    line1, line2 = build_card_now_lines(now_ctx)
    items.append(
        {
            "title": truncate_text(line1, 26),
            "desc": truncate_text(line2, 112),
        }
    )
    astro_desc = build_card_astro_desc(astro)
    if astro_desc:
        items.append({"title": "🌓 日出日落", "desc": astro_desc})
    return items


def select_card_icon(hourly):
    if not hourly:
        return "100"
    first_by_rank = {}
    for item in hourly[:6]:
        text = item.get("text", "")
        icon = item.get("icon", "100")
        if any(k in text for k in ("雨", "雪", "雹")):
            rank = 3
        elif "云" in text or "阴" in text:
            rank = 2
        elif "晴" in text:
            rank = 1
        else:
            rank = 2
        if rank not in first_by_rank:
            first_by_rank[rank] = icon
    best_rank = max(first_by_rank)
    return first_by_rank[best_rank]

CARD_IMAGE_CDN_BASE_DEFAULT = (
    "https://cdn.jsdelivr.net/gh/pr9898/20260709--"
    "@feat/wecom-template-card-detail-page/assets/card"
)

_COVER_PLACEHOLDER_COLORS: dict[str, tuple[str, str, str]] = {
    "sun": ("fbbf24", "1a2029", "Sun"),
    "cloud": ("94a3b8", "1a2029", "Cloud"),
    "rain": ("4ea1ff", "1a2029", "Rain"),
    "thunder": ("a855f7", "1a2029", "Thunder"),
    "snow": ("e2e8f0", "1a2029", "Snow"),
    "fog": ("cbd5e1", "1a2029", "Fog"),
}

_CARD_COVER_WIDTH = 1024
_CARD_COVER_HEIGHT = 455


def icon_cover_category(icon_code: str) -> str:
    try:
        code = int(icon_code)
    except (TypeError, ValueError):
        return "sun"
    if code in (302, 303, 304):
        return "thunder"
    if 300 <= code <= 399:
        return "rain"
    if 400 <= code <= 499:
        return "snow"
    if 500 <= code <= 515:
        return "fog"
    if code in (101, 102, 103, 104, 151, 152, 153, 154):
        return "cloud"
    return "sun"


def card_cover_png_url(icon_code: str) -> str:
    cat = icon_cover_category(icon_code)
    if os.environ.get("CARD_IMAGE_USE_PLACEHOLDER", "").strip() == "1":
        bg, fg, label = _COVER_PLACEHOLDER_COLORS.get(cat, _COVER_PLACEHOLDER_COLORS["sun"])
        text_label = urllib.parse.quote(f"Weather+{label}")
        return (f"https://placehold.co/{_CARD_COVER_WIDTH}x{_CARD_COVER_HEIGHT}/{bg}/{fg}/png?text={text_label}")
    cdn_base = os.environ.get("CARD_IMAGE_CDN_BASE", CARD_IMAGE_CDN_BASE_DEFAULT).strip()
    return f"{cdn_base.rstrip('/')}/{cat}.png"


def source_icon_png_url(icon_code: str) -> str:
    try:
        code = int(icon_code)
    except (TypeError, ValueError):
        return "https://openweathermap.org/img/wn/03d@2x.png"
    day_map = {100: "01d", 101: "02d", 102: "03d", 103: "04d", 104: "04d"}
    night_map = {150: "01n", 151: "02n", 152: "03n", 153: "04n", 154: "04n"}
    if code in day_map:
        owm = day_map[code]
    elif code in night_map:
        owm = night_map[code]
    elif 300 <= code <= 301:
        owm = "09d"
    elif 302 <= code <= 304:
        owm = "11d"
    elif 305 <= code <= 399:
        owm = "10d"
    elif 400 <= code <= 499:
        owm = "13d"
    elif 500 <= code <= 515:
        owm = "50d"
    else:
        owm = "03d"
    return f"https://openweathermap.org/img/wn/{owm}@2x.png"


def ensure_card_assets() -> None:
    root = Path(__file__).resolve().parent
    src_dir = root / "assets" / "card"
    dst_dir = root / "public" / "assets" / "card"
    if not src_dir.is_dir():
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    for png in sorted(src_dir.glob("*.png")):
        dest = dst_dir / png.name
        if not dest.exists():
            shutil.copy2(png, dest)



_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(
            enabled_extensions=("html", "htm", "xml"),
            default_for_string=False,
        ),
    )


def get_jinja_env_json() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=False,
    )


def build_air_quality_context(aq: dict[str, Any] | None) -> dict[str, Any] | None:
    if not aq:
        return None
    category = aq.get("category", "")
    primary = aq.get("primaryPollutant") or ""
    primary_label = _POLLUTANT_LABEL.get(primary, primary.upper()) if primary else ""
    health: dict[str, Any] = aq.get("health") or {}
    advice_text = health.get("effect") or ""
    if not advice_text:
        advice = health.get("advice")
        if isinstance(advice, dict):
            advice_text = advice.get("generalPopulation") or ""
    return {
        "icon": _AQI_ICON.get(category, "🌫️"),
        "aqi": aq.get("aqi", "-"),
        "category": category,
        "primary_label": primary_label,
        "health_advice": advice_text,
    }


def build_astronomy_context(astro: dict[str, Any]) -> dict[str, Any]:
    sun: dict[str, Any] = astro.get("sun") or {}
    moon: dict[str, Any] = astro.get("moon") or {}
    if not sun and not moon:
        return {"sunrise": "", "sunset": "", "moon_phase": "", "empty": True}
    sunrise = format_hour(sun.get("sunrise", "")) if sun.get("sunrise") else ""
    sunset = format_hour(sun.get("sunset", "")) if sun.get("sunset") else ""
    moon_phase = ""
    phase_list: list[dict[str, Any]] = moon.get("moonPhase") or []
    if phase_list:
        moon_phase = phase_list[0].get("name", "")
    else:
        moon_phase = moon.get("name") or moon.get("phase") or ""
    return {
        "sunrise": sunrise,
        "sunset": sunset,
        "moon_phase": moon_phase,
        "empty": not sunrise and not sunset and not moon_phase,
    }


def build_template_context(
    now: dict[str, Any],
    hourly: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    indices: list[dict[str, Any]],
    air_quality: dict[str, Any] | None,
    astronomy: dict[str, Any] | None,
    forecast_3d: list[dict[str, Any]] | None,
    pages_base_url: str,
) -> dict[str, Any]:
    now_dt = datetime.now(TZ)
    header_date = now_dt.strftime("%Y-%m-%d")
    weekday_cn = _WEEKDAY_CN[now_dt.weekday()]
    header_time = now_dt.strftime("%H:%M")

    icon_code = now.get("icon", "100")
    card_image_url = card_cover_png_url(icon_code)
    source_icon_url = source_icon_png_url(icon_code)
    jump_url = pages_base_url or ""

    now_ctx = {
        "icon": now.get("icon", "100"),
        "text": now.get("text", ""),
        "temp": now.get("temp", "-"),
        "feels_like": now.get("feelsLike", "-"),
        "humidity": now.get("humidity", "-"),
        "wind_dir": now.get("windDir", ""),
        "wind_scale": now.get("windScale", ""),
    }

    hourly_24: list[dict[str, Any]] = []
    for item in hourly[:24]:
        fx_time = item.get("fxTime", "")
        hourly_24.append(
            {
                "time": format_hour(fx_time) if fx_time else "--",
                "icon": item.get("icon", "100"),
                "temp": item.get("temp", "-"),
                "text": item.get("text", ""),
                "pop": pop_value(item.get("pop")),
            }
        )

    forecast_list: list[dict[str, Any]] = []
    for index, item in enumerate(forecast_3d or []):
        fx_date = item.get("fxDate", "")
        forecast_list.append(
            {
                "label": format_day_label(fx_date, index) if fx_date else ("今天" if index == 0 else "未来"),
                "icon": item.get("iconDay", "100"),
                "text": item.get("textDay", ""),
                "temp_min": item.get("tempMin", "-"),
                "temp_max": item.get("tempMax", "-"),
            }
        )

    warnings_list: list[dict[str, Any]] = []
    for w in warnings:
        warnings_list.append(
            {
                "title": w.get("headLine") or w.get("headline") or "预警",
                "event": (w.get("eventType") or {}).get("name", ""),
                "level": format_warning_level(w),
            }
        )

    indexed = index_by_type(indices)
    life_keys = [
        ("带伞", ""),
        ("空调", "11"),
        ("衣着", "3"),
        ("紫外线", "5"),
        ("感冒", "9"),
        ("运动", "1"),
        ("旅游", "6"),
        ("舒适度", "8"),
        ("晾晒", "14"),
        ("防晒", "16"),
        ("交通", "15"),
        ("空气扩散", "10"),
    ]
    umbrella = build_umbrella_advice(hourly).replace("**", "")
    life_indices: list[dict[str, str]] = []
    for name, key in life_keys:
        if name == "带伞":
            val = umbrella
        else:
            item = indexed.get(key)
            val = (item or {}).get("category", "") or (item or {}).get("text", "") or "暂无数据"
        life_indices.append({"name": name, "value": val})

    vertical_items = build_card_vertical_items(
        now_ctx, hourly, warnings_list, astronomy or {}
    )

    return {
        "city_name": CITY_NAME,
        "header_date": header_date,
        "weekday_cn": weekday_cn,
        "header_time": header_time,
        "now": {
            "icon": now.get("icon", "100"),
            "text": now.get("text", ""),
            "temp": now.get("temp", "-"),
            "feels_like": now.get("feelsLike", "-"),
            "humidity": now.get("humidity", "-"),
            "wind_dir": now.get("windDir", ""),
            "wind_scale": now.get("windScale", ""),
        },
        "hourly": hourly_24,
        "forecast_3d": forecast_list,
        "warnings": warnings_list,
        "life_indices": life_indices,
        "air_quality": build_air_quality_context(air_quality),
        "astronomy": build_astronomy_context(astronomy or {}),
        "icon_code": icon_code,
        "card_image_url": card_image_url,
        "source_icon_url": source_icon_url,
        "main_title": truncate_text(f"🌤️ {CITY_NAME}", 26),
        "main_desc": truncate_text(f"📅 {header_date} 周{weekday_cn} {header_time}", 30),
        "source_desc": "天气预报",
        "vertical_items": vertical_items,
        "jump_url": jump_url,
    }


def render_detail_html(context: dict[str, Any]) -> str:
    env = get_jinja_env()
    return env.get_template("detail.html.j2").render(**context)


def render_card(context: dict[str, Any]) -> dict[str, Any]:
    env = get_jinja_env_json()
    return json.loads(env.get_template("card.json.j2").render(**context))



def send_wecom_template_card(webhook_url, template_card):
    payload = http_post_json(
        webhook_url,
        {"msgtype": "template_card", "template_card": template_card},
    )
    if payload.get("errcode") != 0:
        raise RuntimeError(f"WeCom webhook error: {payload}")


def send_wecom_template_card_all(webhook_urls, template_card):
    errors = []
    for index, url in enumerate(webhook_urls, start=1):
        masked = mask_webhook_url(url)
        try:
            send_wecom_template_card(url, template_card)
            print(f"✅ 已发送至企业微信 #{index}（{masked}）")
        except Exception as exc:
            print(f"❌ 发送至企业微信 #{index}（{masked}）失败：{exc}", file=sys.stderr)
            errors.append(f"#{index} {masked}: {exc}")
    if errors:
        raise RuntimeError("部分企业微信推送失败：\n" + "\n".join(errors))

def main() -> None:
    api_key = require_env("QWEATHER_API_KEY")
    api_host = require_env("QWEATHER_API_HOST")
    webhook_urls = parse_webhook_urls(require_env("WECOM_WEBHOOK_URL"))
    if not webhook_urls:
        print("Missing environment variable: WECOM_WEBHOOK_URL", file=sys.stderr)
        sys.exit(1)

    now, hourly, warnings, indices = fetch_weather(api_host, api_key)
    air_quality = fetch_air_quality(api_host, api_key)
    astronomy = fetch_astronomy(api_host, api_key)
    forecast_3d = fetch_3d_forecast(api_host, api_key)
    ensure_card_assets()
    pages_base_url = os.environ.get("PAGES_BASE_URL", "").strip()
    context = build_template_context(now, hourly, warnings, indices, air_quality, astronomy, forecast_3d, pages_base_url)
    try:
        html = render_detail_html(context)
        output_dir = "public"
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Detail page written to {output_dir}/index.html")
    except Exception as exc:
        print(f"⚠️  详情页生成失败（{exc}），跳过；继续推送卡片")
    card = render_card(context)
    send_wecom_template_card_all(webhook_urls, card)
    print(f"Weather report sent successfully to {len(webhook_urls)} webhook(s).")


if __name__ == "__main__":
    main()
