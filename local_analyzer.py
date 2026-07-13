import pymorphy3
import re

morph = pymorphy3.MorphAnalyzer()

POS_MAP = {
    "NOUN": "名词", "VERB": "动词", "INFN": "动词", "ADJF": "形容词",
    "ADJS": "形容词", "COMP": "形容词", "NPRO": "代词", "PREP": "前置词",
    "ADVB": "副词", "CONJ": "连接词", "PRCL": "语气词", "NUMR": "数词",
    "INTJ": "感叹词", "PRED": "谓语副词", "GRND": "副动词", "PRTF": "形动词",
    "PRTS": "形动词", "LATN": "外来词", "PNCT": "标点", "UNKN": "未知",
}

GENDER_MAP = {"masc": "阳", "femn": "阴", "neut": "中"}
NUM_MAP = {"sing": "单", "plur": "复"}
CASE_MAP = {
    "nomn": "一格", "gent": "二格", "datv": "三格",
    "accs": "四格", "ablt": "五格", "loct": "六格",
}
ASPECT_MAP = {"perf": "完成体", "impf": "未完成体"}
TENSE_MAP = {"pres": "现在时", "past": "过去时", "futr": "将来时"}
MOOD_MAP = {"indc": "陈述式", "impr": "命令式"}
ANIM_MAP = {"anim": "动物", "inan": "非动物"}
PERSON_MAP = {"1per": "1", "2per": "2", "3per": "3"}
PUNCT = ",.!?;:–—…\"'«»„\"`'()[]{}<>/\\@#$%^&*+=~|№"
PUNCT_CHARS = set(PUNCT)

# 常用功能词用法说明
FUNC_USAGE = {
    "в": "接四格(方向)或六格(地点): 在...里/到...里",
    "на": "接四格(方向)或六格(地点): 在...上/到...上",
    "с": "接二格(从/自)或五格(和/带): 从.../和...一起",
    "из": "接二格: 从...里面",
    "к": "接三格: 朝.../向...",
    "о": "接六格: 关于...",
    "об": "接六格: 关于...",
    "от": "接二格: 从.../离...",
    "до": "接二格: 到.../直到...",
    "для": "接二格: 为了.../对于...",
    "без": "接二格: 没有.../无...",
    "у": "接二格: 在...旁边/某人处",
    "по": "接三格: 沿着.../按照...",
    "за": "接四格(方向)或五格(位置): 在...后面/到...后面",
    "под": "接四格(方向)或五格(位置): 在...下面/到...下面",
    "над": "接五格: 在...上方",
    "перед": "接五格: 在...前面",
    "через": "接四格: 经过.../穿过...",
    "между": "接五格: 在...之间",
    "при": "接六格: 在...条件下/附属于",
    "про": "接四格: 关于...",
    "против": "接二格: 反对.../在...对面",
    "и": "并列连接词: 和/与",
    "а": "对比连接词: 而/可是",
    "но": "转折连接词: 但是",
    "или": "选择连接词: 或者",
    "что": "说明连接词: (引导从句) / 代词: 什么",
    "чтобы": "目的连接词: 为了/以便",
    "если": "条件连接词: 如果",
    "когда": "时间连接词: 当...时",
    "потому": "原因连接词(потому что): 因为",
    "как": "比较/方式连接词: 像.../作为...",
    "не": "否定语气词: 不/没有",
    "даже": "强调语气词: 甚至",
    "только": "限定语气词: 只/仅仅",
    "ли": "疑问语气词: 吗/是否",
    "же": "强调语气词: 正是/到底",
    "вот": "指示语气词: 这就是/瞧",
    # 副词
    "вчера": "时间副词: 昨天",
    "сегодня": "时间副词: 今天",
    "завтра": "时间副词: 明天",
    "сейчас": "时间副词: 现在",
    "теперь": "时间副词: 现在/如今",
    "тогда": "时间副词: 那时/当时",
    "всегда": "时间副词: 总是",
    "никогда": "时间副词: 从不",
    "иногда": "时间副词: 有时",
    "часто": "时间副词: 经常",
    "редко": "时间副词: 很少",
    "здесь": "地点副词: 在这里",
    "там": "地点副词: 在那里",
    "тут": "地点副词: 在这儿",
    "везде": "地点副词: 到处",
    "нигде": "地点副词: 哪里都不",
    "где-то": "地点副词: 在某处",
    "куда": "方向副词: 去哪里",
    "откуда": "方向副词: 从哪里",
    "туда": "方向副词: 去那里",
    "оттуда": "方向副词: 从那里",
    "домой": "方向副词: 回家",
    "хорошо": "方式副词: 好地",
    "плохо": "方式副词: 坏地",
    "быстро": "方式副词: 快速地",
    "медленно": "方式副词: 慢慢地",
    "много": "程度副词: 很多",
    "мало": "程度副词: 很少",
    "очень": "程度副词: 非常/很",
    "совсем": "程度副词: 完全/根本",
    "почти": "程度副词: 几乎",
    "слишком": "程度副词: 太/过于",
    "довольно": "程度副词: 相当/足够",
    "ещё": "程度副词: 还/再",
    "уже": "时间副词: 已经",
    "тоже": "方式副词: 也",
    "также": "方式副词: 同样地",
    "так": "方式副词: 这样/如此",
    "как-то": "方式副词: 不知怎么地/有一次",
    "вместе": "方式副词: 一起",
    "вдруг": "方式副词: 突然",
    "наконец": "时间副词: 终于",
    "снова": "时间副词: 再次",
    "опять": "时间副词: 又/再",
    "потом": "时间副词: 然后/以后",
    "сначала": "时间副词: 起初/先",
    "скоро": "时间副词: 很快/不久",
}

# 俄中词汇表
WORD_DICT = {
    "я": "我", "ты": "你", "он": "他", "она": "她", "оно": "它", "мы": "我们", "вы": "您/你们", "они": "他们",
    "это": "这/这是", "этот": "这个", "тот": "那个", "весь": "全部", "каждый": "每个", "сам": "自己",
    "кто": "谁", "что": "什么", "какой": "什么样的", "чей": "谁的", "где": "在哪里", "куда": "去哪里",
    "откуда": "从哪里", "когда": "什么时候", "как": "如何/像", "почему": "为什么", "сколько": "多少",
    "человек": "人", "год": "年", "время": "时间", "день": "天/日", "рука": "手", "глаз": "眼睛",
    "дело": "事情", "жизнь": "生活生命", "слово": "词语", "место": "地方", "мир": "世界和平", "дом": "房子家",
    "город": "城市", "страна": "国家", "работа": "工作", "сила": "力量", "вопрос": "问题", "деньги": "钱",
    "вода": "水", "земля": "土地地球", "дверь": "门", "ночь": "夜晚", "путь": "道路途径", "ребёнок": "孩子",
    "друг": "朋友", "мать": "母亲", "отец": "父亲", "жена": "妻子", "сестра": "姐妹", "брат": "兄弟",
    "сын": "儿子", "дочь": "女儿", "муж": "丈夫", "имя": "名字", "книга": "书", "стол": "桌子",
    "окно": "窗户", "машина": "汽车", "хлеб": "面包", "любовь": "爱", "помощь": "帮助",
    "быть": "是在", "стать": "成为", "мочь": "能够", "сказать": "说", "говорить": "说话",
    "знать": "知道", "думать": "想认为", "идти": "走去", "ехать": "乘车去", "прийти": "来到",
    "приходить": "来到", "уйти": "离开", "уходить": "离开", "видеть": "看见", "смотреть": "看",
    "слышать": "听见", "слушать": "听", "понимать": "理解", "хотеть": "想要", "любить": "爱喜欢",
    "жить": "生活住", "работать": "工作", "делать": "做", "сделать": "做完", "читать": "读",
    "писать": "写", "брать": "拿", "взять": "拿走", "дать": "给", "давать": "给",
    "есть": "吃/有", "пить": "喝", "спать": "睡觉", "стоять": "站", "сидеть": "坐", "лежать": "躺",
    "хороший": "好的", "плохой": "坏的", "большой": "大的", "маленький": "小的", "новый": "新的",
    "старый": "旧的/老的", "молодой": "年轻的", "красивый": "美丽的", "важный": "重要的",
    "русский": "俄罗斯的", "сильный": "强大的", "слабый": "虚弱的", "быстрый": "快速的",
    "медленный": "慢的", "холодный": "冷的", "тёплый": "温暖的", "белый": "白色的",
    "чёрный": "黑色的", "красный": "红色的", "зелёный": "绿色的", "синий": "蓝色的",
}

def get_translation(lemma):
    return WORD_DICT.get(lemma.lower(), "")

def get_func_usage(lemma):
    """获取功能词用法说明"""
    return FUNC_USAGE.get(lemma.lower(), "")


def guess_word(word):
    """pymorphy3 不认识时的启发式猜测（优先级：专名 → 尾巴 → 兜底）"""
    raw = word
    w = word.strip(PUNCT + " ")
    if not w:
        return {"text": w, "lemma": raw, "pos": "标点", "analysis": {}, "translation": ""}
    lower = w.lower()

    def _ret(pos, analysis=None, lemma=None):
        return {"text": w, "lemma": lemma or lower, "pos": pos,
                "analysis": analysis or {}, "translation": get_translation(lemma or lower)}

    # ── 优先级1：专有名词（首字母大写） ──
    if w[0].isupper() and not w.isupper() and len(w) > 1:
        return {"text": w, "lemma": w, "pos": "名词（专有）",
                "analysis": {"gender": _guess_gender(w), "number": "单", "animate": "动物"},
                "translation": get_translation(w)}

    # ── 优先级2：动词 → 看尾巴4-5字符 ──
    # 过去时
    for sfx in ["овал", "ивал", "ывал", "евал", "нул", "ался", "ился", "ылся"]:
        if lower.endswith(sfx):
            return {"text": w, "lemma": lower, "pos": "动词",
                    "analysis": {"aspect": "未完成体" if sfx in ("ивал","ывал","евал") else "完成体",
                                 "tense": "过去时", "reflexive": "带-ся" if "ся" in sfx else "不带-ся"}}
    if lower.endswith(("лся", "лась", "лось", "лись")):
        return {"text": w, "lemma": lower, "pos": "动词",
                "analysis": {"aspect": None, "tense": "过去时", "reflexive": "带-ся"}}

    # 不定式
    for sfx in ["овать", "евать", "ивать", "ывать", "нуть", "аться", "иться", "еться"]:
        if lower.endswith(sfx):
            return {"text": w, "lemma": lower, "pos": "动词",
                    "analysis": {"aspect": "未完成体" if sfx in ("ивать","ывать") else "完成体",
                                 "reflexive": "带-ся" if "ся" in sfx else "不带-ся"}}
    if lower.endswith(("ть", "ти", "чь")):
        return {"text": w, "lemma": lower, "pos": "动词",
                "analysis": {"aspect": "未完成体" if lower.endswith(("ать","ять","еть")) else "完成体",
                             "reflexive": "带-ся" if "ся" in lower else "不带-ся"}}

    # 现在时/将来时第三人称
    for sfx in ["ает", "яет", "ует", "юет", "ивает", "ывает", "аются", "яются"]:
        if lower.endswith(sfx):
            return {"text": w, "lemma": lower, "pos": "动词",
                    "analysis": {"aspect": "未完成体", "tense": "现在时", "reflexive": "带-ся" if "ся" in sfx else "不带-ся"}}
    if lower.endswith(("ет", "ёт", "ит", "ют", "ут", "ят", "ат")):
        return {"text": w, "lemma": lower, "pos": "动词",
                "analysis": {"aspect": None, "tense": "现在时", "reflexive": "不带-ся"}}

    # 副动词
    if lower.endswith(("ав", "яв", "ив", "ыв", "авши", "явши", "учи", "ючи", "аясь", "ясь")):
        return {"text": w, "lemma": lower, "pos": "副动词", "analysis": {}}
    if lower.endswith(("а", "я")) and len(lower) > 4 and lower[-3:-1] in ("вш", "ш"):
        return {"text": w, "lemma": lower, "pos": "副动词", "analysis": {}}

    # 形动词
    if lower.endswith(("ущий", "ющий", "ащий", "ящий", "вший", "ший")):
        return {"text": w, "lemma": lower, "pos": "形动词", "analysis": {"tense": "现在时" if lower.endswith(("щий",)) else "过去时"}}
    if lower.endswith(("емый", "имый", "омый", "нный", "тый")):
        return {"text": w, "lemma": lower, "pos": "形动词", "analysis": {"tense": "现在时" if lower.endswith(("емый","имый","омый")) else "过去时"}}

    # ── 优先级3：名词 → 后缀4+字符 ──
    for sfx, gen in [("ость", "阴"), ("есть", "阴"), ("ность", "阴"), ("тель", "阳"),
                     ("ение", "中"), ("ание", "中"), ("ство", "中"), ("ствие", "中"),
                     ("ция", "阴"), ("сия", "阴"), ("ация", "阴"), ("фикация", "阴"),
                     ("ота", "阴"), ("ина", "阴"), ("изм", "阳"), ("аж", "阳")]:
        if lower.endswith(sfx):
            return {"text": w, "lemma": lower, "pos": "名词",
                    "analysis": {"gender": gen, "number": "单", "case": "一格", "animate": "非动物"}}

    # 指小/表爱
    for sfx, gen in [("очка", "阴"), ("ечка", "阴"), ("онька", "阴"), ("енька", "阴"),
                     ("ик", "阳"), ("чик", "阳"), ("ок", "阳"), ("ёк", "阳")]:
        if lower.endswith(sfx):
            return {"text": w, "lemma": lower, "pos": "名词",
                    "analysis": {"gender": gen, "number": "单", "case": "一格"}}

    # 性别短尾巴
    if lower.endswith(("а", "я")):
        return {"text": w, "lemma": lower, "pos": "名词",
                "analysis": {"gender": "阴", "number": "单", "case": "一格"}}
    if lower.endswith(("о", "е", "ие")):
        return {"text": w, "lemma": lower, "pos": "名词",
                "analysis": {"gender": "中", "number": "单", "case": "一格"}}
    if lower.endswith(("ь",)):
        return {"text": w, "lemma": lower, "pos": "名词",
                "analysis": {"gender": "阴" if lower.endswith(("ость","сть","чь","шь","щь")) else "阳", "number": "单"}}
    if lower.endswith(("й",)):
        return {"text": w, "lemma": lower, "pos": "名词",
                "analysis": {"gender": "阳", "number": "单", "case": "一格"}}
    if lower[-1] in "бвгдзклмнпрстфхцчшщ" and len(lower) >= 2:
        return {"text": w, "lemma": lower, "pos": "名词",
                "analysis": {"gender": "阳", "number": "单", "case": "一格"}}

    # ── 优先级4：形容词 → 后缀 ──
    if lower.endswith(("ский", "цкий", "чный", "жный", "шний", "овой", "евой")):
        return {"text": w, "lemma": lower, "pos": "形容词",
                "analysis": {"gender": "阳", "number": "单", "case": "一格", "form": "长尾"}}
    if lower.endswith(("ый", "ий", "ой")):
        return {"text": w, "lemma": lower, "pos": "形容词",
                "analysis": {"gender": "阳", "number": "单", "case": "一格", "form": "长尾"}}
    if lower.endswith(("ая", "яя")):
        return {"text": w, "lemma": lower, "pos": "形容词",
                "analysis": {"gender": "阴", "number": "单", "case": "一格", "form": "长尾"}}
    if lower.endswith(("ое", "ее")):
        return {"text": w, "lemma": lower, "pos": "形容词",
                "analysis": {"gender": "中", "number": "单", "case": "一格", "form": "长尾"}}
    if lower.endswith(("ые", "ие")):
        return {"text": w, "lemma": lower, "pos": "形容词",
                "analysis": {"number": "复", "case": "一格", "form": "长尾"}}

    # ── 优先级5：副词 ──
    if lower.endswith(("ески", "цки", "ому", "ему", "ком", "ьи", "ами")):
        return {"text": w, "lemma": lower, "pos": "副词", "analysis": {"degree": "原级"}}
    if lower.endswith("о") and len(lower) > 2 and not lower.endswith(("то", "но")):
        return {"text": w, "lemma": lower, "pos": "副词", "analysis": {"degree": "原级"}}

    # ── 兜底 ──
    # 纯数字
    if w.isdigit():
        return {"text": w, "lemma": w, "pos": "数词", "analysis": {}}

    # 短词（可能是前置词/连接词/语气词）
    if len(w) <= 3 and w.isalpha():
        return {"text": w, "lemma": lower, "pos": "功能词", "analysis": {}}

    return {"text": word, "lemma": lower, "pos": "未知", "analysis": {}}


def _guess_gender(w):
    if w.endswith(("а", "я", "ия")):
        return "阴"
    if w.endswith(("о", "е")):
        return "中"
    return "阳"


def infer_pos_from_tag(tag):
    """pymorphy3 返回了形态但 POS 为空时，从格/时态等反推词性"""
    if tag.case and tag.gender:
        return "名词"
    if tag.tense or tag.aspect:
        return "动词"
    if tag.gender and tag.number and tag.case:
        return "形容词"
    return "未知"


def analyze_word(word):
    """pymorphy3 词法分析，返回 dict"""
    # 分离标点——这是导致大量"未知"的根本原因
    clean = word.strip(PUNCT + " ")
    if not clean:
        return {"text": word, "lemma": word, "pos": "标点", "analysis": {}}

    parses = morph.parse(clean)
    if not parses:
        return guess_word(clean)

    p = parses[0]
    tag = p.tag
    pos_tag = tag.POS or ""
    pos_cn = POS_MAP.get(pos_tag)
    if not pos_cn:
        pos_cn = infer_pos_from_tag(tag)
    lemma = p.normal_form

    analysis = {}
    # pymorphy3 有 POS 则按 POS 分析，否则从形态推断
    if pos_tag in ("NOUN",) or pos_cn == "名词":
        analysis["gender"] = GENDER_MAP.get(str(tag.gender), str(tag.gender)) if tag.gender else None
        analysis["number"] = NUM_MAP.get(str(tag.number), str(tag.number)) if tag.number else None
        analysis["case"] = CASE_MAP.get(str(tag.case), str(tag.case)) if tag.case else None
        analysis["animate"] = ANIM_MAP.get(str(tag.animacy), str(tag.animacy)) if tag.animacy else None

    elif pos_tag in ("VERB", "INFN") or pos_cn == "动词":
        analysis["aspect"] = ASPECT_MAP.get(str(tag.aspect), str(tag.aspect)) if tag.aspect else None
        analysis["transitive"] = "及物" if "tran" in str(tag.transitivity) else "不及物" if tag.transitivity else None
        analysis["reflexive"] = "带-ся" if "Refl" in str(tag) else "不带-ся"
        analysis["person"] = PERSON_MAP.get(str(tag.person), str(tag.person)) if tag.person else None
        analysis["number"] = NUM_MAP.get(str(tag.number), str(tag.number)) if tag.number else None
        analysis["tense"] = TENSE_MAP.get(str(tag.tense), str(tag.tense)) if tag.tense else None
        analysis["mood"] = MOOD_MAP.get(str(tag.mood), str(tag.mood)) if tag.mood else None

    elif pos_tag in ("ADJF", "ADJS", "COMP") or pos_cn == "形容词":
        analysis["gender"] = GENDER_MAP.get(str(tag.gender), str(tag.gender)) if tag.gender else None
        analysis["number"] = NUM_MAP.get(str(tag.number), str(tag.number)) if tag.number else None
        analysis["case"] = CASE_MAP.get(str(tag.case), str(tag.case)) if tag.case else None
        form = str(tag)
        if "Short" in form:
            analysis["form"] = "短尾"
        elif "COMP" in str(pos_tag):
            analysis["form"] = "比较级"
        else:
            analysis["form"] = "长尾"

    elif pos_tag in ("NPRO",):
        analysis["gender"] = GENDER_MAP.get(str(tag.gender), str(tag.gender)) if tag.gender else None
        analysis["number"] = NUM_MAP.get(str(tag.number), str(tag.number)) if tag.number else None
        analysis["case"] = CASE_MAP.get(str(tag.case), str(tag.case)) if tag.case else None

    elif pos_tag in ("PREP",):
        analysis["governs"] = CASE_MAP.get(str(tag.case), str(tag.case)) if tag.case else None
        analysis["usage"] = get_func_usage(lemma)

    elif pos_tag in ("ADVB",):
        analysis["usage"] = get_func_usage(lemma)

    elif pos_tag in ("CONJ", "PRCL", "INTJ"):
        analysis["usage"] = get_func_usage(lemma)

    return {"text": clean, "lemma": lemma, "pos": pos_cn, "analysis": analysis, "translation": get_translation(lemma)}


def analyze_sentence(tokens):
    """基于格规则的句式分析：按从句整段截取，不拆词"""
    # 从句连接词
    SUBORDINATORS = {"что", "чтобы", "когда", "если", "потому", "как", "который", "которая",
                     "которое", "которые", "где", "куда", "откуда", "пока", "хотя",
                     "поэтому", "так", "чем", "чей", "чья", "чьё", "чьи"}

    # 找从句分割点
    split_idx = -1
    for i, w in enumerate(tokens):
        if w["lemma"].lower() in SUBORDINATORS and i > 0:
            split_idx = i
            break

    components = []
    if split_idx > 0:
        main_text = " ".join(t["text"] for t in tokens[:split_idx])
        sub_text = " ".join(t["text"] for t in tokens[split_idx:])
        main_analysis = _summarize_clause(tokens[:split_idx])
        sub_analysis = _summarize_clause(tokens[split_idx:])
        components.append({"role": "主句", "text": main_text, "desc": main_analysis})
        components.append({"role": "从句", "text": sub_text, "desc": sub_analysis})
    else:
        full_text = " ".join(t["text"] for t in tokens)
        analysis = _summarize_clause(tokens)
        components.append({"role": "单句", "text": full_text, "desc": analysis})

    return components


def _summarize_clause(tokens):
    """总结从句结构特征"""
    subj = next((t for t in tokens if t["pos"] in ("名词", "代词") and t["analysis"].get("case") == "一格"), None)
    pred = next((t for t in tokens if t["pos"] == "动词"), None)
    obj = next((t for t in tokens if t["pos"] in ("名词", "代词") and t["analysis"].get("case") == "四格"), None)
    advs = [t for t in tokens if t["pos"] == "副词"]
    preps = [t for t in tokens if t["pos"] == "前置词"]

    parts = []
    if subj and pred:
        info = f"{pred['analysis'].get('aspect','')} {pred['analysis'].get('tense','')}".strip() or ""
        parts.append(f"主语「{subj['text']}」+ 谓语「{pred['text']}」（{info}）")
    elif pred:
        parts.append(f"无人称/不定人称句，谓语「{pred['text']}」")
    else:
        parts.append("称名/省略句")

    if obj:
        case = obj["analysis"].get("case", "")
        parts.append(f"宾语「{obj['text']}」（{case}）")
    if advs:
        parts.append(f"状语：{'、'.join(t['text'] for t in advs)}")
    if preps:
        parts.append(f"含前置词：{'、'.join(t['text'] for t in preps)}")

    return "；".join(parts)


def local_analyze(text):
    """本地完整分析：分句 → 分词 → 词法 → 句式"""
    # 拆分句子
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    all_tokens = []
    all_sentences = []

    for sent_text in sentences:
        raw_tokens = re.findall(r"[а-яёА-ЯЁa-zA-Z0-9]+|[^\s]", sent_text)
        tokens = []
        for t in raw_tokens:
            clean = t.strip(PUNCT + " ")
            if clean and any(c.isalpha() or c.isdigit() for c in clean):
                w = analyze_word(clean)
                if "translation" not in w:
                    w["translation"] = get_translation(w.get("lemma", clean))
                tokens.append(w)
        components = analyze_sentence(tokens)

        # 从句概括
        main_c = next((c for c in components if c["role"] == "主句"), None)
        sub_c = next((c for c in components if c["role"] == "从句"), None)
        single_c = next((c for c in components if c["role"] == "单句"), None)

        summary_parts = []
        if single_c:
            summary_parts.append(f"单句：{single_c['desc']}")
        if main_c:
            summary_parts.append(f"▎主句：{main_c['desc']}")
        if sub_c:
            summary_parts.append(f"▎从句：{sub_c['desc']}")

        all_tokens.extend(tokens)
        all_sentences.append({
            "text": sent_text,
            "summary": "；".join(summary_parts) or f"共{len(tokens)}个词",
            "components": components,
        })

    return {
        "chinese": f"[本地模式：翻译请用 LLM 模式]",
        "literal": " ".join(t["lemma"] for t in all_tokens),
        "sentence": {
            "summary": f"共 {len(all_sentences)} 个句子",
            "components": [],
            "sentences": all_sentences,
        },
        "words": all_tokens,
    }
