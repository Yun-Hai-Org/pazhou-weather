import type { Slot } from "./types";

const BEIJING_OFFSET_MS = 8 * 60 * 60 * 1000;
const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];

export function beijingNow(now = new Date()): Date {
  return new Date(now.getTime() + BEIJING_OFFSET_MS);
}

export function businessSlot(now = new Date()): { date: string; slot: Slot; time: string; weekday: string } {
  const bj = beijingNow(now);
  const iso = bj.toISOString();
  const date = iso.slice(0, 10);
  const hour = Number(iso.slice(11, 13));
  return { date, slot: hour < 12 ? "am" : "pm", time: iso.slice(11, 16), weekday: WEEKDAYS[bj.getUTCDay()] };
}

export function nextAlarmIso(now = new Date()): number {
  const bj = beijingNow(now);
  const iso = bj.toISOString();
  const date = iso.slice(0, 10);
  const currentMinutes = Number(iso.slice(11, 13)) * 60 + Number(iso.slice(14, 16));
  const targets = [6 * 60 + 5, 17 * 60 + 5];
  let target = targets.find((minute) => minute > currentMinutes);
  let day = date;
  if (target === undefined) {
    target = targets[0];
    day = new Date(Date.parse(`${date}T00:00:00Z`) + 86_400_000).toISOString().slice(0, 10);
  }
  // Parse the Beijing wall-time target as UTC, then subtract the fixed UTC+8 offset.
  const beijingWallEpoch = Date.parse(`${day}T${String(Math.floor(target / 60)).padStart(2, "0")}:${String(target % 60).padStart(2, "0")}:00.000Z`);
  return beijingWallEpoch - BEIJING_OFFSET_MS;
}
