import type { Holiday } from "./types";

interface HolidayData { days?: Array<{ date: string; isOffDay: boolean }> }

export async function resolveHoliday(date: string): Promise<Holiday> {
  const weekend = new Date(`${date}T00:00:00Z`).getUTCDay();
  try {
    const response = await fetch(`https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/${date.slice(0, 4)}.json`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json() as HolidayData;
    const day = data.days?.find((item) => item.date === date);
    const isRest = weekend === 0 || weekend === 6 || day?.isOffDay === true;
    return { label: isRest ? "休息日" : "法定工作日", source: "holiday-cn" };
  } catch {
    return { label: weekend === 0 || weekend === 6 ? "休息日" : "法定工作日", source: "weekend-fallback" };
  }
}
