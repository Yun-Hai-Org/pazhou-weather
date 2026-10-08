import type { Slot, SolarTerm, SolarTermMeta } from "./types";

export const SOLAR_TERMS: SolarTermMeta[] = [
  { name: "立春", poem: "春风如贵客，一到便繁华。", author: "袁枚", origin: "春风" },
  { name: "雨水", poem: "好雨知时节，当春乃发生。", author: "杜甫", origin: "春夜喜雨" },
  { name: "惊蛰", poem: "微雨众卉新，一雷惊蛰始。", author: "韦应物", origin: "观田家" },
  { name: "春分", poem: "春分雨脚落声微，柳岸斜风带客归。", author: "徐铉", origin: "春分日" },
  { name: "清明", poem: "清明时节雨纷纷，路上行人欲断魂。", author: "杜牧", origin: "清明" },
  { name: "谷雨", poem: "谷雨春光晓，山川黛色青。", author: "元稹", origin: "咏廿四气诗·谷雨春光晓" },
  { name: "立夏", poem: "绿树阴浓夏日长，楼台倒影入池塘。", author: "高骈", origin: "山亭夏日" },
  { name: "小满", poem: "小满气全时，如何靡草衰。", author: "元稹", origin: "咏廿四气诗·小满四月中" },
  { name: "芒种", poem: "时雨及芒种，四野皆插秧。", author: "陆游", origin: "时雨" },
  { name: "夏至", poem: "昼晷已云极，宵漏自此长。", author: "韦应物", origin: "夏至避暑北池" },
  { name: "小暑", poem: "倏忽温风至，因循小暑来。", author: "元稹", origin: "咏廿四气诗·小暑六月节" },
  { name: "大暑", poem: "桂轮开子夜，萤火照空时。", author: "元稹", origin: "咏廿四气诗·大暑六月中" },
  { name: "立秋", poem: "云天收夏色，木叶动秋声。", author: "刘言史", origin: "立秋" },
  { name: "处暑", poem: "离离暑云散，袅袅凉风起。", author: "白居易", origin: "早秋曲江感怀" },
  { name: "白露", poem: "蒹葭苍苍，白露为霜。", author: "佚名", origin: "诗经·蒹葭" },
  { name: "秋分", poem: "金气秋分，风清露冷秋期半。", author: "谢逸", origin: "点绛唇·金气秋分" },
  { name: "寒露", poem: "袅袅凉风动，凄凄寒露零。", author: "白居易", origin: "池上" },
  { name: "霜降", poem: "霜叶红于二月花。", author: "杜牧", origin: "山行" },
  { name: "立冬", poem: "冻笔新诗懒写，寒炉美酒时温。", author: "李白", origin: "立冬" },
  { name: "小雪", poem: "晚来天欲雪，能饮一杯无。", author: "白居易", origin: "问刘十九" },
  { name: "大雪", poem: "孤舟蓑笠翁，独钓寒江雪。", author: "柳宗元", origin: "江雪" },
  { name: "冬至", poem: "天时人事日相催，冬至阳生春又来。", author: "杜甫", origin: "小至" },
  { name: "小寒", poem: "小寒连大吕，欢鹊垒新巢。", author: "元稹", origin: "咏廿四气诗·小寒十二月节" },
  { name: "大寒", poem: "大寒岁底庆团圆。", author: "陆游", origin: "大寒出江陵西门" }
];

export function solarTermFor(date: string, slot: Slot = "am"): SolarTerm | null {
  // Approximate fixed dates in the current century. Exact astronomical dates vary by at most one day.
  const ranges: Array<[string, number]> = [
    ["02-04", 0], ["02-19", 1], ["03-05", 2], ["03-20", 3], ["04-05", 4], ["04-20", 5],
    ["05-05", 6], ["05-21", 7], ["06-06", 8], ["06-21", 9], ["07-07", 10], ["07-22", 11],
    ["08-07", 12], ["08-23", 13], ["09-07", 14], ["09-23", 15], ["10-08", 16], ["10-23", 17],
    ["11-07", 18], ["11-22", 19], ["12-07", 20], ["12-21", 21], ["01-05", 22], ["01-20", 23]
  ];
  const monthDay = date.slice(5);
  const match = ranges.find(([day]) => day === monthDay);
  if (!match) return null;
  const index = match[1];
  const meta = SOLAR_TERMS[index];
  return {
    termIndex: index,
    ...meta,
    poem: slot === "pm" ? meta.eveningPoem ?? meta.poem : meta.poem,
    imageUrl: `assets/solar-terms/${index + 1}.jpg`
  };
}
