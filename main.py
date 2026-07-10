import gzip
import json
import os
from typing import Any
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

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
    indices = qweather_get(host, api_key, "/v7/indices/1d", {"type": "3,5,9,11,1,2,6,8"}).get("daily", [])
    return now, hourly, warnings, indices


def fetch_air_quality(host: str, api_key: str) -> dict[str, Any] | None:
    # 空气质量实况接口（免费全球，1×1 km 分辨率）。
    # 任一异常均优雅降级：返回 None，不阻断整体推送。
    try:
        return qweather_get(host, api_key, "/v7/airquality/now").get("now")
    except Exception as exc:  # noqa: BLE001 - 网络/接口异常统一降级
        print(f"⚠️  空气质量接口请求失败（{exc}），跳过")
        return None


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


def build_next_3h_lines(hourly: list[dict]) -> list[str]:
    lines = []
    for item in hourly[:3]:
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
        return _COLOR_LABEL.get(color, color)
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
    next_3h = hourly[:3]
    for item in next_3h:
        if is_rainy_text(item.get("text", "")) or pop_value(item.get("pop")) >= UMBRELLA_POP_THRESHOLD:
            return "☂️ **建议带伞**（未来 3 小时降水概率偏高或有雨雪）"
    return "😎 **无需带伞**"


_INDEX_ICONS = {
    "带伞": "☂️",
    "空调": "❄️",
    "衣着": "👕",
    "紫外线": "🔆",
    "感冒": "🤧",
    "运动": "🏃",
    "洗车": "🚿",
    "旅游": "🧳",
    "舒适度": "🛋️",
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


def build_air_quality_lines(aq: dict[str, Any] | None) -> str:
    if not aq:
        return "🌫️ 暂无空气质量数据"
    aqi = aq.get("aqi", "-")
    category = aq.get("category", "")
    primary = aq.get("primary", "")
    primary_text = f"　主要污染物 `{primary}`" if primary and primary != "NA" else ""
    icon = _AQI_ICON.get(category, "🌫️")
    line = f"{icon} **AQI {aqi}　{category}**{primary_text}"
    # 部分套餐返回健康建议（label/strategy 字段），有则附带
    advice: dict[str, Any] = aq.get("health") or {}
    advice_text = advice.get("effect") or advice.get("advice") or ""
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


def build_message(
    now: dict[str, Any],
    hourly: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    indices: list[dict[str, Any]],
    air_quality: dict[str, Any] | None = None,
    astronomy: dict[str, Any] | None = None,
) -> str:
    now_text_icon = "🌤️" if "晴" in now['text'] else ("☁️" if "云" in now['text'] or "阴" in now['text'] else "🌧️")
    feels = now.get("feelsLike")
    feels_part = f"　|　🤚 体感 **{feels}°C**" if feels else ""
    now_text = (
        f"{now_text_icon} **{now['text']}　{now['temp']}°C**"
        f"{feels_part}\n"
        f"　　💧 湿度 **{now.get('humidity', '-')}%**　|　"
        f"🌬️ {now.get('windDir', '')} **{now.get('windScale', '')}级**"
    )

    next_3h = "\n".join(build_next_3h_lines(hourly))
    summary_24h = build_24h_summary(hourly)
    warning_lines = build_warning_lines(warnings)
    indexed = index_by_type(indices)

    umbrella_advice = build_umbrella_advice(hourly)
    if "建议带伞" in umbrella_advice:
        umbrella_text = "建议带伞（未来 3 小时可能下雨）"
    else:
        umbrella_text = "无需带伞"
    life_lines = [
        format_index_line("带伞", {"category": "", "text": umbrella_text}),
        format_index_line("空调", indexed.get("11")),
        format_index_line("衣着", indexed.get("3")),
        format_index_line("紫外线", indexed.get("5")),
        format_index_line("感冒", indexed.get("9")),
        format_index_line("运动", indexed.get("1")),
        format_index_line("洗车", indexed.get("2")),
        format_index_line("旅游", indexed.get("6")),
        format_index_line("舒适度", indexed.get("8")),
    ]

    header_date = datetime.now(TZ).strftime("%Y-%m-%d")
    header_time = datetime.now(TZ).strftime("%H:%M")
    weekday_cn = ["一", "二", "三", "四", "五", "六", "日"][datetime.now(TZ).weekday()]
    warning_text = "\n".join(warning_lines)
    life_text = "\n".join(life_lines)
    air_quality_text = build_air_quality_lines(air_quality)
    astronomy_text = build_astronomy_lines(astronomy or {})

    return (
        f"## 🌈 {CITY_NAME}天气预报　<font color=\"comment\">{header_date} 周{weekday_cn} {header_time}</font>\n"
        f"{now_text}\n\n"
        f"#### ⏰ 未来 3 小时\n"
        f"{next_3h}\n\n"
        f"#### 📅 未来 24 小时\n"
        f"{summary_24h}\n\n"
        f"#### 🚨 气象预警\n"
        f"{warning_text}\n\n"
        f"#### 🌫️ 空气质量\n"
        f"{air_quality_text}\n\n"
        f"#### 💡 生活提醒\n"
        f"{life_text}\n\n"
        f"{astronomy_text}\n\n"
        f"<font color=\"comment\">— 数据来源：和风天气 · 自动推送 🌦️</font>"
    )


def send_wecom_markdown(webhook_url: str, content: str) -> None:
    payload = http_post_json(
        webhook_url,
        {"msgtype": "markdown", "markdown": {"content": content}},
    )
    if payload.get("errcode") != 0:
        raise RuntimeError(f"WeCom webhook error: {payload}")


def main() -> None:
    api_key = require_env("QWEATHER_API_KEY")
    api_host = require_env("QWEATHER_API_HOST")
    webhook_url = require_env("WECOM_WEBHOOK_URL")

    now, hourly, warnings, indices = fetch_weather(api_host, api_key)
    air_quality = fetch_air_quality(api_host, api_key)
    astronomy = fetch_astronomy(api_host, api_key)
    message = build_message(now, hourly, warnings, indices, air_quality, astronomy)
    send_wecom_markdown(webhook_url, message)
    print("Weather report sent successfully.")


if __name__ == "__main__":
    main()
