import type { Slot, SolarTerm, SolarTermMeta } from "./types";

export const SOLAR_TERMS: SolarTermMeta[] = [
  {
    name: "立春",
    poem: "春风如贵客，一到便繁华。",
    eveningPoem: "春风又绿江南岸，明月何时照我还。",
    eveningAuthor: "王安石",
    eveningOrigin: "泊船瓜洲",
    author: "袁枚",
    origin: "春风"
  },
  {
    name: "雨水",
    poem: "好雨知时节，当春乃发生。",
    eveningPoem: "天街小雨润如酥，草色遥看近却无。",
    eveningAuthor: "韩愈",
    eveningOrigin: "早春呈水部张十八员外",
    author: "杜甫",
    origin: "春夜喜雨"
  },
  {
    name: "惊蛰",
    poem: "微雨众卉新，一雷惊蛰始。",
    eveningPoem: "今夜偏知春气暖，虫声新透绿窗纱。",
    eveningAuthor: "刘方平",
    eveningOrigin: "月夜",
    author: "韦应物",
    origin: "观田家"
  },
  {
    name: "春分",
    poem: "春分雨脚落声微，柳岸斜风带客归。",
    eveningPoem: "春色满园关不住，一枝红杏出墙来。",
    eveningAuthor: "叶绍翁",
    eveningOrigin: "游园不值",
    author: "徐铉",
    origin: "春分日"
  },
  {
    name: "清明",
    poem: "清明时节雨纷纷，路上行人欲断魂。",
    eveningPoem: "素衣莫起风尘叹，犹及清明可到家。",
    eveningAuthor: "陆游",
    eveningOrigin: "临安春雨初霁",
    author: "杜牧",
    origin: "清明"
  },
  {
    name: "谷雨",
    poem: "谷雨春光晓，山川黛色青。",
    eveningPoem: "沾衣欲湿杏花雨，吹面不寒杨柳风。",
    eveningAuthor: "志南",
    eveningOrigin: "绝句",
    author: "元稹",
    origin: "咏廿四气诗·谷雨春光晓"
  },
  {
    name: "立夏",
    poem: "绿树阴浓夏日长，楼台倒影入池塘。",
    eveningPoem: "小荷才露尖尖角，早有蜻蜓立上头。",
    eveningAuthor: "杨万里",
    eveningOrigin: "小池",
    author: "高骈",
    origin: "山亭夏日"
  },
  {
    name: "小满",
    poem: "小满气全时，如何靡草衰。",
    eveningPoem: "乡村四月闲人少，才了蚕桑又插田。",
    eveningAuthor: "翁卷",
    eveningOrigin: "乡村四月",
    author: "元稹",
    origin: "咏廿四气诗·小满四月中"
  },
  {
    name: "芒种",
    poem: "时雨及芒种，四野皆插秧。",
    eveningPoem: "夜来南风起，小麦覆陇黄。",
    eveningAuthor: "白居易",
    eveningOrigin: "观刈麦",
    author: "陆游",
    origin: "时雨"
  },
  {
    name: "夏至",
    poem: "昼晷已云极，宵漏自此长。",
    eveningPoem: "接天莲叶无穷碧，映日荷花别样红。",
    eveningAuthor: "杨万里",
    eveningOrigin: "晓出净慈寺送林子方",
    author: "韦应物",
    origin: "夏至避暑北池"
  },
  {
    name: "小暑",
    poem: "倏忽温风至，因循小暑来。",
    eveningPoem: "荷风送香气，竹露滴清响。",
    eveningAuthor: "孟浩然",
    eveningOrigin: "夏日南亭怀辛大",
    author: "元稹",
    origin: "咏廿四气诗·小暑六月节"
  },
  {
    name: "大暑",
    poem: "桂轮开子夜，萤火照空时。",
    eveningPoem: "黑云翻墨未遮山，白雨跳珠乱入船。",
    eveningAuthor: "苏轼",
    eveningOrigin: "六月二十七日望湖楼醉书",
    author: "元稹",
    origin: "咏廿四气诗·大暑六月中"
  },
  {
    name: "立秋",
    poem: "云天收夏色，木叶动秋声。",
    eveningPoem: "空山新雨后，天气晚来秋。",
    eveningAuthor: "王维",
    eveningOrigin: "山居秋暝",
    author: "刘言史",
    origin: "立秋"
  },
  {
    name: "处暑",
    poem: "离离暑云散，袅袅凉风起。",
    eveningPoem: "残暑蝉催尽，新秋雁戴来。",
    eveningAuthor: "白居易",
    eveningOrigin: "早秋曲江感怀",
    author: "白居易",
    origin: "早秋曲江感怀"
  },
  {
    name: "白露",
    poem: "蒹葭苍苍，白露为霜。",
    eveningPoem: "露从今夜白，月是故乡明。",
    eveningAuthor: "杜甫",
    eveningOrigin: "月夜忆舍弟",
    author: "佚名",
    origin: "诗经·蒹葭"
  },
  {
    name: "秋分",
    poem: "金气秋分，风清露冷秋期半。",
    eveningPoem: "银烛秋光冷画屏，轻罗小扇扑流萤。",
    eveningAuthor: "杜牧",
    eveningOrigin: "秋夕",
    author: "谢逸",
    origin: "点绛唇·金气秋分"
  },
  {
    name: "寒露",
    poem: "袅袅凉风动，凄凄寒露零。",
    eveningPoem: "可怜九月初三夜，露似真珠月似弓。",
    eveningAuthor: "白居易",
    eveningOrigin: "暮江吟",
    author: "白居易",
    origin: "池上"
  },
  {
    name: "霜降",
    poem: "霜叶红于二月花。",
    eveningPoem: "月落乌啼霜满天，江枫渔火对愁眠。",
    eveningAuthor: "张继",
    eveningOrigin: "枫桥夜泊",
    author: "杜牧",
    origin: "山行"
  },
  {
    name: "立冬",
    poem: "冻笔新诗懒写，寒炉美酒时温。",
    eveningPoem: "细雨生寒未有霜，庭前木叶半青黄。",
    eveningAuthor: "仇远",
    eveningOrigin: "立冬即事二首",
    author: "李白",
    origin: "立冬"
  },
  {
    name: "小雪",
    poem: "晚来天欲雪，能饮一杯无。",
    eveningPoem: "绿蚁新醅酒，红泥小火炉。",
    eveningAuthor: "白居易",
    eveningOrigin: "问刘十九",
    author: "白居易",
    origin: "问刘十九"
  },
  {
    name: "大雪",
    poem: "孤舟蓑笠翁，独钓寒江雪。",
    eveningPoem: "燕山雪花大如席，片片吹落轩辕台。",
    eveningAuthor: "李白",
    eveningOrigin: "北风行",
    author: "柳宗元",
    origin: "江雪"
  },
  {
    name: "冬至",
    poem: "天时人事日相催，冬至阳生春又来。",
    eveningPoem: "邯郸驿里逢冬至，抱膝灯前影伴身。",
    eveningAuthor: "白居易",
    eveningOrigin: "邯郸冬至夜思家",
    author: "杜甫",
    origin: "小至"
  },
  {
    name: "小寒",
    poem: "小寒连大吕，欢鹊垒新巢。",
    eveningPoem: "寒夜客来茶当酒，竹炉汤沸火初红。",
    eveningAuthor: "杜耒",
    eveningOrigin: "寒夜",
    author: "元稹",
    origin: "咏廿四气诗·小寒十二月节"
  },
  {
    name: "大寒",
    poem: "大寒岁底庆团圆。",
    eveningPoem: "大寒雪未消，闭户不能出。",
    eveningAuthor: "陆游",
    eveningOrigin: "大寒出江陵西门",
    author: "陆游",
    origin: "大寒出江陵西门"
  }
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
  const isEvening = slot === "pm";
  return {
    termIndex: index,
    ...meta,
    poem: isEvening ? meta.eveningPoem ?? meta.poem : meta.poem,
    author: isEvening ? meta.eveningAuthor ?? meta.author : meta.author,
    origin: isEvening ? meta.eveningOrigin ?? meta.origin : meta.origin,
    imageUrl: `assets/solar-terms/${index + 1}.jpg`
  };
}
