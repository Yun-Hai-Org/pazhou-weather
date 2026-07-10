import gzip
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

GUANGZHOU_LOCATION = "101280101"
CITY_NAME = "广州"
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


def qweather_get(host: str, api_key: str, path: str, params: dict | None = None) -> dict:
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


def fetch_weather(host: str, api_key: str) -> tuple[dict, list[dict], list[dict], list[dict]]:
    now = qweather_get(host, api_key, "/v7/weather/now")["now"]
    hourly = qweather_get(host, api_key, "/v7/weather/24h")["hourly"]
    try:
        warning_payload = qweather_get(host, api_key, "/v7/warning/now")
        warnings = warning_payload.get("warning") or []
    except (RuntimeError, urllib.error.HTTPError):
        print("⚠️  预警接口不可用（需要付费套餐），跳过")
        warnings = []
    indices = qweather_get(host, api_key, "/v7/indices/1d", {"type": "3,5,9,11"}).get("daily", [])
    return now, hourly, warnings, indices


def build_next_3h_lines(hourly: list[dict]) -> list[str]:
    lines = []
    for item in hourly[:3]:
        pop = pop_value(item.get("pop"))
        lines.append(
            f"{format_hour(item['fxTime'])} {item['text']} {item['temp']}°C 降水{pop}%"
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
    def parse_wind_scale(s: str) -> int:
        try:
            return max(int(x) for x in s.split("-"))
        except (ValueError, TypeError):
            return 0

    wind_scales = [parse_wind_scale(item.get("windScale", "0")) for item in hourly if item.get("windScale")]
    if wind_scales:
        wind_summary = f"风力{min(wind_scales)}-{max(wind_scales)}级"
    else:
        wind_summary = "风力未知"
    rain_text = "有雨" if has_rain else "无雨"
    return f"{min_temp}~{max_temp}°C · {rain_text} · {wind_summary}"


def build_warning_lines(warnings: list[dict]) -> list[str]:
    if not warnings:
        return ["无"]
    lines = []
    for item in warnings:
        title = item.get("title") or item.get("typeName") or "预警"
        level = item.get("level") or item.get("severity") or ""
        if level:
            lines.append(f"- {title}（{level}）")
        else:
            lines.append(f"- {title}")
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
            return "建议带伞（未来3小时降水概率偏高或有雨雪）"
    return "无需带伞"


def format_index_line(name: str, item: dict | None) -> str:
    if not item:
        return f"- {name}：暂无数据"
    category = item.get("category", "")
    text = item.get("text", "")
    if category and text:
        return f"- {name}：{category}，{text}"
    if category:
        return f"- {name}：{category}"
    return f"- {name}：{text or '暂无数据'}"


def build_message(now: dict, hourly: list[dict], warnings: list[dict], indices: list[dict]) -> str:
    now_text = (
        f"**实况** {now['text']} {now['temp']}°C "
        f"湿度{now.get('humidity', '-')}%% "
        f"{now.get('windDir', '')}{now.get('windScale', '')}级"
    )

    next_3h = "\n".join(build_next_3h_lines(hourly))
    summary_24h = build_24h_summary(hourly)
    warning_lines = build_warning_lines(warnings)
    indexed = index_by_type(indices)

    life_lines = [
        f"- 带伞：{build_umbrella_advice(hourly)}",
        format_index_line("空调", indexed.get("11")),
        format_index_line("衣着", indexed.get("3")),
        format_index_line("紫外线", indexed.get("5")),
        format_index_line("感冒", indexed.get("9")),
    ]

    header_time = datetime.now(TZ).strftime("%m-%d %H:%M")
    warning_text = "\n".join(warning_lines)
    life_text = "\n".join(life_lines)

    return (
        f"## {CITY_NAME}天气 · {header_time}\n"
        f"{now_text}\n\n"
        f"**未来3小时**\n"
        f"{next_3h}\n\n"
        f"**未来24小时** {summary_24h}\n\n"
        f"**预警**\n"
        f"{warning_text}\n\n"
        f"**生活提醒**\n"
        f"{life_text}"
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
    message = build_message(now, hourly, warnings, indices)
    send_wecom_markdown(webhook_url, message)
    print("Weather report sent successfully.")


if __name__ == "__main__":
    main()
