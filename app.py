import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json, os
from datetime import datetime
from local_analyzer import local_analyze

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="俄语翻译与语法分析器", layout="wide",
                   menu_items={"About": None, "Report a bug": None, "Get help": None})

DEEPSEEK_BASE = "https://api.deepseek.com"
DEFAULT_KEY = st.secrets.get("DEEPSEEK_KEY", "") if hasattr(st, "secrets") else ""
OLLAMA_BASE = "http://localhost:11434/v1"

CATEGORY_COLORS = {
    "名词": "#4CAF50", "动词": "#F44336", "形容词": "#2196F3",
    "代词": "#FF9800", "前置词": "#9C27B0", "副词": "#00BCD4",
    "连接词": "#795548", "语气词": "#607D8B", "数词": "#E91E63",
}

SYSTEM_PROMPT = """你是俄语语言学专家。对用户输入的俄语句子，严格按以下三阶段分析，以 JSON 格式输出。

## 阶段1：翻译
- chinese: 通顺的中文翻译
- literal: 逐词直译

## 阶段2：句式分析
关键原则：俄语句子成分由格决定，非词序。主语必定一格，直接宾语四格，间接宾语三格，前置词短语看接格。
- summary: 用流畅中文概括句意（1-2句）
- components: 句子成分列表，按顺序排列。每项含 role、text(俄语原文词组)、desc(中文说明)

成分分析规则：
1. 主语：一格名词/代词，动作发出者或被描述对象
2. 谓语：动词（含时体态人称信息）或系词+表语。无人称句注明"无人称"
3. 直接宾语：四格名词/代词（不带前置词）
4. 间接宾语：三格名词/代词
5. 定语：形容词/物主代词/二格名词修饰另一名词，与其被修饰词同数同格
6. 状语：表时间/地点/方式/原因/目的等，可为副词或前置词短语。注：前置词短语中名词格取决于前置词，仔细辨别
7. 补语/表语：系词后的名词/形容词（在五格或一格）

关键鉴别技巧：
- 一格 ≠ 一定是主语（如"Это книга"中книга是一格表语）
- 及物动词+四格 → 动宾关系；不及物动词+其他格 → 状语/补语
- -ся动词不带直接宾语
- 无人称动词无主语，逻辑主体用三格

示例：
"summary": "陈述句：昨天我在图书馆读了一本有趣的书。"
"components": [
  {"role": "主语", "text": "я", "desc": "一格人称代词，行为发出者"},
  {"role": "谓语", "text": "читал", "desc": "未完成体过去时，及物动词，接四格"},
  {"role": "直接宾语", "text": "интересную книгу", "desc": "四格，定语интересную修饰книгу，同阴性单数四格"},
  {"role": "时间状语", "text": "Вчера", "desc": "时间副词"},
  {"role": "地点状语", "text": "в библиотеке", "desc": "前置词в接六格，表地点"}
]

## 阶段3：逐词分析
words 数组，每个词：
- text: 原文
- lemma: 原形
- pos: 词性（名词/动词/形容词/代词/前置词/副词/连接词/语气词/数词/感叹词）
- analysis: 按词性不同字段：

名词：gender(阳/阴/中), number(单/复), case(1-6格用中文:一格/二格/三格/四格/五格/六格), animate(动物/非动物), declension(第1/2/3变格法)
动词：aspect(完成体/未完成体), transitive(及物/不及物), government(接格关系,如"接四格"), reflexive(带-ся/不带-ся), person(1/2/3), number(单/复), tense(现在时/过去时/将来时), mood(陈述式/命令式/假定式), impersonal(是/否)
形容词：gender, number, case, form(长尾/短尾), degree(原级/比较级/最高级)
代词：category(人称/物主/指示/疑问/反身/限定/不定/否定), gender, number, case
前置词：governs(支配格，如"接六格")
副词：category(方式/地点/时间/程度/目的/原因), degree(原级/比较级/最高级)
连接词：category(并列/主从)
语气词：function(疑问/强调/否定/限定/指示)
数词：type(基数词/序数词/集合数词), gender, number, case

## 输出要求
只输出 JSON，不要 markdown 代码块，不要任何额外文字。

## 术语参考
- 一格(именительный), 二格(родительный), 三格(дательный), 四格(винительный), 五格(творительный), 六格(предложный)
- 完成体(СВ), 未完成体(НСВ)
- 第1变格法(а/я结尾), 第2变格法(辅音/о/е结尾), 第3变格法(ь结尾阴性)
"""

EXAMPLE_INPUT = "Вчера я читал интересную книгу в библиотеке."
EXAMPLE_OUTPUT = """
{
  "chinese": "昨天我在图书馆读了一本有趣的书。",
  "literal": "昨天 我 读 有趣的 书 在 图书馆",
  "sentence": {
    "summary": "陈述句：昨天我在图书馆读了一本有趣的书。",
    "components": [
      {"role": "主语", "text": "я", "desc": "一格人称代词，行为发出者"},
      {"role": "谓语", "text": "читал", "desc": "未完成体过去时，及物动词，接四格"},
      {"role": "直接宾语", "text": "интересную книгу", "desc": "四格，定语интересную修饰книгу，同阴性单数四格"},
      {"role": "时间状语", "text": "Вчера", "desc": "时间副词"},
      {"role": "地点状语", "text": "в библиотеке", "desc": "前置词в接六格，表地点"}
    ]
  },
  "words": [
    {"text": "Вчера", "lemma": "вчера", "pos": "副词", "analysis": {"category": "时间", "degree": "原级"}},
    {"text": "я", "lemma": "я", "pos": "代词", "analysis": {"category": "人称", "gender": null, "number": "单", "case": "一格"}},
    {"text": "читал", "lemma": "читать", "pos": "动词", "analysis": {"aspect": "未完成体", "transitive": "及物", "government": "接四格", "reflexive": "不带-ся", "person": "1", "number": "单", "tense": "过去时", "mood": "陈述式", "impersonal": "否"}},
    {"text": "интересную", "lemma": "интересный", "pos": "形容词", "analysis": {"gender": "阴", "number": "单", "case": "四格", "form": "长尾", "degree": "原级"}},
    {"text": "книгу", "lemma": "книга", "pos": "名词", "analysis": {"gender": "阴", "number": "单", "case": "四格", "animate": "非动物", "declension": "第1变格法"}},
    {"text": "в", "lemma": "в", "pos": "前置词", "analysis": {"governs": "接六格"}},
    {"text": "библиотеке", "lemma": "библиотека", "pos": "名词", "analysis": {"gender": "阴", "number": "单", "case": "六格", "animate": "非动物", "declension": "第1变格法"}}
  ]
}
"""

SCORE_PROMPT = """你是翻译质量评审专家。请从以下五个维度对译文打分（每项1-5分，5为最优），只输出 JSON。

维度：
- semantic(语义保真度): 原文含义是否完整传达
- fluency(语法通顺度): 是否符合中文表达习惯
- register(语体匹配度): 口语/书面语语级是否匹配
- cultural(文化对等度): 专有名词文化概念处理是否得当
- rhetoric(修辞传达度): 修辞手法是否恰当转化

输入格式：{original: 俄语原文, chinese: 中文译文}
只输出 JSON，不要其他文字。"""

TRANSLATE_PROMPT = "将以下俄语句子翻译成中文，同时给出逐词直译。只输出 JSON：{\"chinese\": \"中文译文\", \"literal\": \"逐词直译\"}"

OLLAMA_TRANSLATE_PROMPT = "翻译这句俄语为中文。先输出自然的中文译文，换行后输出逐词直译。"

CN_RU_PROMPT = "将以下中文翻译成俄语。只输出俄语句子，不要多余内容。"
OLLAMA_CN_RU_PROMPT = "将这句中文翻译成俄语。只输出俄语句子。"

FIX_UNKNOWN_PROMPT = """你是俄语词法专家。分析以下俄语单词，只输出 JSON 数组，每个词格式：
{"text":"原文","lemma":"原形","pos":"词性","analysis":{...}}
analysis 字段同之前的词法分析格式。"""

OLLAMA_FIX_PROMPT = "分析这些俄语单词的词性、原形和语法特征。"


def safe_parse_translation(raw):
    """兼容性解析翻译结果"""
    try:
        return parse_json(raw)
    except json.JSONDecodeError:
        lines = raw.strip().split("\n")
        chinese = lines[0].strip() if lines else raw.strip()
        literal = lines[1].strip() if len(lines) > 1 else ""
        return {"chinese": chinese, "literal": literal}


def call_deepseek(api_key, model, system, user, thinking=True):
    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE)
    
    messages = []
    if thinking:
        messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            extra_body={"thinking": {"type": "enabled"}},
        )
        return response.choices[0].message.content
    else:
        messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return response.choices[0].message.content


def parse_json(raw):
    text = raw.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def call_ollama(model, system, user):
    """调用本地 Ollama 模型"""
    client = OpenAI(api_key="ollama", base_url=OLLAMA_BASE)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content


def render_score(score_data):
    dims = [
        ("semantic", "语义保真度", "原文含义是否完整传达"),
        ("fluency", "语法通顺度", "是否符合中文表达习惯"),
        ("register", "语体匹配度", "语级是否匹配"),
        ("cultural", "文化对等度", "文化概念处理是否得当"),
        ("rhetoric", "修辞传达度", "修辞手法是否恰当转化"),
    ]
    
    total = 0
    for key, label, desc in dims:
        val = score_data.get(key, 0)
        total += val
        color = "#F44336" if val <= 2 else "#FF9800" if val <= 3 else "#4CAF50"
        st.markdown(f"**{label}** ({desc})")
        st.progress(val / 5, text=f"{val}/5")


# ====== UI ======

# 初始化 session state
if "api_key" not in st.session_state:
    st.session_state.api_key = DEFAULT_KEY
if "model" not in st.session_state:
    st.session_state.model = "deepseek-v4-pro"
if "deep_think" not in st.session_state:
    st.session_state.deep_think = True
if "use_local" not in st.session_state:
    st.session_state.use_local = True
if "use_ollama" not in st.session_state:
    st.session_state.use_ollama = True
if "ollama_model" not in st.session_state:
    st.session_state.ollama_model = "qwen2.5:1.5b"
if "enable_score" not in st.session_state:
    st.session_state.enable_score = False
if "history" not in st.session_state:
    st.session_state.history = []
if "direction" not in st.session_state:
    st.session_state.direction = "俄→中"

# 主题 CSS（仅隐藏 Deploy 按钮）
# 美化样式
try:
    with open(os.path.join(BASE_DIR, "bg_b64.txt"), encoding="ascii") as f:
        BG_IMAGE = f.read().strip()
except FileNotFoundError:
    BG_IMAGE = ""

THEME_CSS = f"""
<style>
[data-testid="stDeployButton"] {{display:none}}
</style>
<style>

.stApp {{
    background-image: url({BG_IMAGE})!important;
    background-size: cover!important;
    background-position: center!important;
    background-attachment: fixed!important;
}}
.stApp::before {{
    content: ''; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.18);
    z-index: 0; pointer-events: none;
}}
[data-testid="stAppViewContainer"] {{background: transparent!important}}
[data-testid="stHeader"] {{background: transparent!important}}

h1 {{text-align:center!important; font-size:2.8rem!important; font-weight:800!important;
    color:#64b5f6!important; -webkit-text-fill-color:#64b5f6!important;
    text-shadow:0 2px 6px rgba(0,0,0,0.6)}}
.stCaption {{text-align:center!important; font-size:1.1rem!important; margin-bottom:2.5rem!important;
    color:#ffffff!important; font-weight:500;
    text-shadow:0 1px 3px rgba(0,0,0,0.7)}}
h1::after {{content:'';display:block;width:80px;height:4px;
    background:linear-gradient(90deg,#0d47a1,#1e88e5 40%,#e53935 40%,#e53935 70%,#fff 70%);
    border-radius:2px;margin:16px auto 0}}
</style>
"""

st.markdown(THEME_CSS, unsafe_allow_html=True)

# 菜单汉化
components.html("""
<script>
setTimeout(function(){
    var map = {"Rerun":"重新运行","Settings":"设置","About":"关于","Report a bug":"报告问题","Get help":"获取帮助","Print":"打印","Clear cache":"清除缓存","Auto rerun":"自动重新运行","Record screen":"录制屏幕","Made with Streamlit":"由 Streamlit 驱动"};
    var all = window.parent.document.querySelectorAll('*');
    for(var i=0;i<all.length;i++){
        var t = all[i].textContent.trim();
        if(!t || all[i].children.length) continue;
        for(var k in map){ if(t.startsWith(k)){ all[i].textContent = map[k]; break; } }
    }
}, 800);
</script>
""", height=0)

st.markdown("""
<style>
.stTextArea textarea {
    border-radius:14px!important; border:1px solid rgba(255,255,255,0.2)!important;
    font-size:1.1rem!important; padding:18px!important; color:#ffffff!important;
    transition:all .3s!important; min-height:120px!important;
    background:rgba(255,255,255,0.08)!important;
    box-shadow:none!important;
}
.stTextArea textarea:focus {border-color:rgba(255,255,255,0.4)!important; box-shadow:0 0 0 3px rgba(255,255,255,0.1)!important}

.stButton > button {
    border-radius:14px!important; font-size:1.1rem!important; font-weight:700!important;
    padding:14px 40px!important; background:linear-gradient(135deg,#0d47a1,#1565c0,#1e88e5)!important;
    border:none!important; color:#fff!important; transition:all .3s!important;
    box-shadow:0 4px 16px rgba(13,71,161,.35)!important; letter-spacing:1px
}
.stButton > button:hover {
    transform:translateY(-2px)!important; box-shadow:0 8px 25px rgba(13,71,161,.5)!important
}

.stSuccess, .stInfo, .stError, .stWarning,
[data-testid="stAlert"] {
    border-radius:12px!important; box-shadow:none!important;
    background:rgba(255,255,255,0.06)!important; border:1px solid rgba(255,255,255,0.1)!important;
}
[data-testid="stNotification"] {background:rgba(255,255,255,0.06)!important}

.stMetric {background:var(--secondary-background-color)!important; border-radius:10px!important;
    padding:12px!important; border:1px solid rgba(128,128,128,0.15)!important}

[data-testid="stExpander"] {border-radius:12px!important; transition:all .2s!important}
[data-testid="stExpander"]:hover {box-shadow:0 2px 12px rgba(0,0,0,0.03)!important}

hr {border-color:rgba(128,128,128,0.12)!important;margin:2rem 0!important}

.stTextArea textarea::placeholder {opacity:0.5}

h2 {font-size:1.25rem!important; font-weight:700!important; letter-spacing:1px;
    border-left:4px solid #1e88e5; padding-left:14px; color:#ffffff!important;
    text-shadow:0 1px 3px rgba(0,0,0,0.7)}
h3 {font-size:1.05rem!important; font-weight:600!important;
    border-left:3px solid #1565c0;padding-left:12px; color:#ccc!important;
    text-shadow:0 1px 3px rgba(0,0,0,0.7)}

p, span, label {color: #e0e0e0; text-shadow:0 1px 3px rgba(0,0,0,0.7)}
.stTextArea label {color: #e0e0e0!important; font-weight:600}
.stCaption, .stCaptionContainer {color:#fff!important}
blockquote {color: #fff!important; border-left-color: rgba(255,255,255,0.3)!important}
</style>
""", unsafe_allow_html=True)

# 顶部栏：设置按钮
col_top1, col_top2 = st.columns([1, 20])
with col_top1:
    with st.popover("⚙️"):
        st.markdown("### API 设置")
        st.session_state.api_key = st.text_input(
            "API Key", value=st.session_state.api_key, type="password",
            help="使用你自己的 DeepSeek API Key，费用由 Key 持有者承担"
        )
        st.session_state.model = st.selectbox(
            "模型", ["deepseek-v4-pro", "deepseek-v4-flash"],
            index=0 if st.session_state.model == "deepseek-v4-pro" else 1
        )
        st.caption(f"接口地址：{DEEPSEEK_BASE}")
        st.caption("费用按 API Key 持有者的 DeepSeek 账户计费。")
        st.divider()
        st.session_state.use_local = st.toggle(
            "本地分析模式", value=st.session_state.use_local,
            help="pymorphy3 本地语法分析（零费用、零幻觉）"
        )
        st.session_state.use_ollama = st.toggle(
            "Ollama 本地翻译", value=st.session_state.use_ollama,
            help="使用本地 Ollama 模型翻译，完全免费。需先安装 Ollama"
        )
        if st.session_state.use_ollama:
            st.session_state.ollama_model = st.text_input(
                "Ollama 模型", value=st.session_state.ollama_model,
                help="如 qwen2.5:1.5b, gemma3:4b"
            )
            st.caption(f"服务地址：{OLLAMA_BASE}")
            st.caption("终端运行: ollama pull 模型名 下载")
        if not st.session_state.use_ollama:
            st.divider()
            st.session_state.deep_think = st.toggle(
                "深度思考", value=st.session_state.deep_think,
                help="开启后分析更细致但速度较慢"
            )
            st.session_state.enable_score = st.toggle(
                "翻译评分", value=st.session_state.enable_score,
                help="开启后对翻译质量打分（额外耗时）"
            )

# 居中内容区
_, center_col, _ = st.columns([1, 3, 1])
with center_col:
    st.markdown("""
    <div style="text-align:center;padding:2rem 0 .5rem">
    </div>
    """, unsafe_allow_html=True)
    st.title("俄语句子翻译与语法分析")
    st.caption("输入一句俄语，智能分析其翻译、句式与逐词语法")

    dir_col1, dir_col2 = st.columns([1, 4])
    with dir_col1:
        new_dir = st.toggle("中↔俄", value=st.session_state.direction == "中→俄", key="dir_toggle",
                       help="开启：中→俄 / 关闭：俄→中")
        st.session_state.direction = "中→俄" if new_dir else "俄→中"
    
    input_text = st.text_area(
        "输入俄语句子" if st.session_state.direction == "俄→中" else "输入中文句子",
        placeholder="例如：Вчера я читал интересную книгу в библиотеке." if st.session_state.direction == "俄→中" else "例如：昨天我在图书馆读了一本有趣的书。",
        height=100
    )

    analyze_btn = st.button("开始分析", type="primary", use_container_width=True)

if analyze_btn and input_text.strip():
    with st.spinner("正在分析中，请稍候..."):
        try:
            if st.session_state.direction == "中→俄":
                # 中→俄：LLM 翻译 → 本地分析俄语句子
                if st.session_state.use_ollama:
                    ru_text = call_ollama(
                        model=st.session_state.ollama_model,
                        system=OLLAMA_CN_RU_PROMPT,
                        user=input_text,
                    )
                else:
                    ru_text = call_deepseek(
                        api_key=st.session_state.api_key,
                        model=st.session_state.model,
                        system=CN_RU_PROMPT,
                        user=input_text,
                        thinking=False,
                    )
                ru_text = ru_text.strip()
                data = local_analyze(ru_text)
                data["chinese"] = ru_text
                data["source_cn"] = input_text
            elif st.session_state.use_local:
                # 本地语法分析
                data = local_analyze(input_text)
                # 调试：列出未知词
                unk = [w["text"] for w in data.get("words", []) if w["pos"] in ("未知", "其他", "功能词")]
                if unk:
                    st.warning(f"本地分析未识别词：{', '.join(unk)}，正在 LLM 补全...")
                # LLM 补全未知词
                unknown_words = [w for w in data.get("words", []) if w["pos"] in ("未知", "其他", "功能词")]
                if unknown_words:
                    with st.spinner("本地分析完成，正在补全未知词..."):
                        try:
                            unknown_text = ", ".join(w["text"] for w in unknown_words)
                            if st.session_state.use_ollama:
                                fix_raw = call_ollama(
                                    model=st.session_state.ollama_model,
                                    system=OLLAMA_FIX_PROMPT,
                                    user=unknown_text,
                                )
                            else:
                                fix_raw = call_deepseek(
                                    api_key=st.session_state.api_key,
                                    model=st.session_state.model,
                                    system=FIX_UNKNOWN_PROMPT,
                                    user=unknown_text,
                                    thinking=False,
                                )
                            fixed = json.loads(fix_raw)
                            if isinstance(fixed, list):
                                for fw in fixed:
                                    for w in data["words"]:
                                        if w["text"] == fw.get("text"):
                                            w["pos"] = fw.get("pos", w["pos"])
                                            w["lemma"] = fw.get("lemma", w["lemma"])
                                            w["analysis"] = fw.get("analysis", w["analysis"])
                        except Exception:
                            pass
                # 翻译：Ollama 或 DeepSeek
                try:
                    if st.session_state.use_ollama:
                        tl_raw = call_ollama(
                            model=st.session_state.ollama_model,
                            system=OLLAMA_TRANSLATE_PROMPT,
                            user=input_text,
                        )
                        tl = safe_parse_translation(tl_raw)
                    else:
                        tl_raw = call_deepseek(
                            api_key=st.session_state.api_key,
                            model=st.session_state.model,
                            system=TRANSLATE_PROMPT,
                            user=input_text,
                            thinking=False,
                        )
                        tl = parse_json(tl_raw)
                    data["chinese"] = tl.get("chinese", "")
                    data["literal"] = tl.get("literal", "")
                except Exception as e:
                    msg = str(e)
                    if "Connection" in msg or "connect" in msg.lower():
                        msg = "Ollama 未启动，请在终端运行 ollama serve"
                    data["chinese"] = f"[翻译失败：{msg}]"
                    data["literal"] = ""
            else:
                raw = call_deepseek(
                    api_key=st.session_state.api_key,
                    model=st.session_state.model,
                    system=SYSTEM_PROMPT,
                    user=f"分析以下俄语句子：{input_text}\n\n输出 JSON 格式参考：\n{EXAMPLE_OUTPUT}",
                    thinking=st.session_state.deep_think,
                )
                data = parse_json(raw)
            
            st.session_state.result_data = data
            st.session_state.result_input = input_text
            st.session_state.word_page = 1

            # 保存历史（最多20条，FIFO）
            entry = {
                "time": datetime.now().strftime("%m/%d %H:%M"),
                "input": input_text,
                "chinese": data.get("chinese", "")[:80],
                "data": data,
            }
            st.session_state.history.insert(0, entry)
            if len(st.session_state.history) > 20:
                st.session_state.history = st.session_state.history[:20]
            
        except json.JSONDecodeError as e:
            st.session_state.result_data = None
            st.error(f"模型返回格式异常：{e}")
            with st.expander("查看原始响应"):
                st.text(raw)
        except Exception as e:
            st.session_state.result_data = None
            st.error(f"请求失败：{e}")
            st.caption("提示：检查网络连接，或尝试切换模型（flash ↔ pro）")

elif analyze_btn:
    st.warning("请输入句子")

# ── 显示缓存结果（翻页时不会丢失） ──
data = st.session_state.get("result_data")
if data:
    input_text = st.session_state.get("result_input", "")

    # ===== Stage 1: Translation =====
    if st.session_state.direction == "俄→中":
        st.header("翻译")
        st.success(f"**中文译文**\n\n{data.get('chinese', '')}")
    else:
        st.header("译文")
        source = data.get("source_cn", "")
        ru = data.get("chinese", "")
        st.markdown(f"**中文原文**\n\n> {source}")
        st.success(f"**俄语译文**\n\n{ru}")

    # Score (optional)
    if st.session_state.get("enable_score"):
        with st.spinner("正在评估翻译质量..."):
            score_raw = call_deepseek(
                api_key=st.session_state.api_key, model=st.session_state.model,
                system=SCORE_PROMPT,
                user=json.dumps({"original": input_text, "chinese": data.get("chinese", "")}, ensure_ascii=False),
                thinking=False,
            )
            try:
                score_data = parse_json(score_raw)
                with st.expander("翻译质量评分"):
                    render_score(score_data)
            except json.JSONDecodeError:
                st.warning("评分生成失败")

    # ===== Stage 2: Sentence =====
    st.header("句式分析")
    sent = data.get("sentence", {})

    sentences = sent.get("sentences", [])
    if sentences:
        for si, s in enumerate(sentences):
            st.subheader(f"第 {si+1} 句")
            st.markdown(f"> {s.get('text', '')}")
            
            summary = s.get("summary", "")
            if summary:
                st.markdown(
                    f"""<div style="background:rgba(128,128,128,0.06);border:1px solid rgba(128,128,128,0.15);
                    border-radius:12px;padding:16px 20px;font-size:0.95rem;line-height:1.8;margin-bottom:16px;
                    color:#ffffff">{summary}</div>""",
                    unsafe_allow_html=True,
                )

            components = s.get("components", [])
            if components:
                rows = ""
                for c in components:
                    role = c.get("role", "")
                    color = "#4da6ff" if "主" in role else "#6c5ce7" if "从" in role else "#00b894"
                    rows += f"""<div style="padding:12px 0;border-bottom:1px solid rgba(128,128,128,0.2)">
                    <span style="background:{color};color:#fff;border-radius:6px;padding:3px 12px;
                    font-weight:600;font-size:0.85rem">{role}</span>
                    <div style="margin-top:8px;font-size:0.95rem;color:#ffffff"><b>{c.get('text','')}</b></div>
                    <div style="color:#ffffff;opacity:0.85;font-size:0.85rem;margin-top:4px">{c.get('desc','')}</div></div>"""
                st.markdown(
                    f'<div style="border:1px solid rgba(128,128,128,0.15);border-radius:12px;padding:8px 20px;background:rgba(128,128,128,0.03)">{rows}</div>',
                    unsafe_allow_html=True,
                )
    else:
        # 兼容旧格式
        summary = sent.get("summary", "")
        components = sent.get("components", [])
        if summary:
            st.markdown(
                f"""<div style="background:rgba(128,128,128,0.06);border:1px solid rgba(128,128,128,0.15);
                border-radius:12px;padding:16px 20px;font-size:0.95rem;line-height:1.8;margin-bottom:16px;
                color:#ffffff">{summary}</div>""",
                unsafe_allow_html=True,
            )
        if components:
            rows = ""
            for c in components:
                role = c.get("role", "")
                color = "#4da6ff" if "主" in role else "#6c5ce7" if "从" in role else "#00b894"
                rows += f"""<div style="padding:12px 0;border-bottom:1px solid rgba(128,128,128,0.2)">
                <span style="background:{color};color:#fff;border-radius:6px;padding:3px 12px;
                font-weight:600;font-size:0.85rem">{role}</span>
                <div style="margin-top:8px;font-size:0.95rem;color:#ffffff"><b>{c.get('text','')}</b></div>
                <div style="color:#ffffff;opacity:0.85;font-size:0.85rem;margin-top:4px">{c.get('desc','')}</div></div>"""
            st.markdown(
                f'<div style="border:1px solid rgba(128,128,128,0.15);border-radius:12px;padding:8px 20px;background:rgba(128,128,128,0.03)">{rows}</div>',
                unsafe_allow_html=True,
            )

    # ===== Stage 3: Words =====
    st.header("逐词分析")
    words = data.get("words", [])
    total = len(words)

    page_size = 10
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = st.session_state.get("word_page", 1)
    if page > total_pages:
        page = st.session_state.word_page = 1

    start = (page - 1) * page_size
    end = min(start + page_size, total)
    page_words = words[start:end]

    st.caption(f"共 {total} 个词，第 {start+1}-{end} 个")

    for i, word in enumerate(page_words, start=start):
        pos = word.get("pos", "")
        lemma = word.get("lemma", "?")
        trans = word.get("translation", "")
        header = f"{i+1}. {word['text']}  →  {lemma}  [{pos}]"
        if trans:
            header += f"  —  {trans}"
        with st.expander(header):
            items = []
            for k, v in word.get("analysis", {}).items():
                if v is not None:
                    labels = {"gender":"性","number":"数","case":"格","animate":"动物性","declension":"变格法",
                              "aspect":"体","transitive":"及物性","government":"接格关系","reflexive":"反身性",
                              "person":"人称","tense":"时态","mood":"式","impersonal":"无人称",
                              "form":"形式","degree":"级别","category":"类别","governs":"支配格",
                              "function":"功能","type":"类型","usage":"用法"}
                    items.append(f"**{labels.get(k,k)}**：{v}")
            if items:
                st.markdown(" | ".join(items))
            st.markdown(f"[查看完整用法 →](https://ru.wiktionary.org/wiki/{lemma})")

    if total_pages > 1:
        cols = st.columns([1, 1, 3])
        with cols[0]:
            if st.button("← 上一页", disabled=page <= 1):
                st.session_state.word_page = page - 1
                st.rerun()
        with cols[1]:
            if st.button("下一页 →", disabled=page >= total_pages):
                st.session_state.word_page = page + 1
                st.rerun()
        with cols[2]:
            st.caption(f"第 {page}/{total_pages} 页")

# ── 历史记录 ──
with st.expander(f"历史记录 ({len(st.session_state.history)} 条)"):
    if not st.session_state.history:
        st.caption("暂无记录")
    else:
        for i, h in enumerate(st.session_state.history):
            cols = st.columns([1, 3, 6, 1])
            cols[0].caption(h["time"])
            cols[1].caption(h["input"][:40] + ("..." if len(h["input"]) > 40 else ""))
            cols[2].caption(h.get("chinese", ""))
            if cols[3].button("查看", key=f"hist_{i}"):
                st.session_state.result_data = h.get("data")
                st.session_state.result_input = h["input"]
                st.session_state.word_page = 1
                st.rerun()
