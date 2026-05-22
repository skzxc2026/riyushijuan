import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "rebuild"
TRANSLATE_CACHE = OUT / "translation_cache.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def normalize_text(text: str) -> str:
    table = str.maketrans({
        "１": "1", "２": "2", "３": "3", "４": "4", "５": "5",
        "６": "6", "７": "7", "８": "8", "９": "9", "０": "0",
        "．": ".", "，": ",", "　": " ",
    })
    return re.sub(r"[ \t]+", " ", text.translate(table))


def extract_answer_map(text: str) -> dict[int, str]:
    text = normalize_text(text)
    answers: dict[int, str] = {}
    # 表格型：题号行 + 答案行
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for i, line in enumerate(lines[:-1]):
        if "题号" not in line or "答案" not in lines[i + 1]:
            continue
        nums = [int(x) for x in re.findall(r"\d+", line)]
        vals = re.findall(r"[A-D]|[ぁ-んァ-ン一-龥ー]+", re.sub(r"答案|评分标准.*", "", lines[i + 1]))
        for n, v in zip(nums, vals):
            if 1 <= n <= 60:
                answers[n] = v

    # 行内型：1. B 2. C ...
    for n, v in re.findall(r"(?<!\d)([1-5]?\d|60)\s*[.、．]\s*([A-D]|[ぁ-んァ-ン一-龥ー]+)", text):
        ni = int(n)
        if 1 <= ni <= 60:
            answers[ni] = v
    return dict(sorted(answers.items()))


def validate_answers(name: str, answers: dict[int, str]) -> None:
    missing = [i for i in range(1, 61) if i not in answers]
    if missing:
        raise SystemExit(f"{name} 答案缺少题号: {missing}")


def guangdong_verified_answers() -> dict[int, str]:
    vals = [
        "A", "B", "C", "C", "A", "B", "B", "A", "B", "C",
        "C", "B", "B", "A", "C", "B", "B", "A", "A", "B",
        "C", "A", "B", "A", "D", "A", "B", "D", "D", "C",
        "B", "C", "C", "D", "A", "B", "C", "D", "C", "A",
        "C", "D", "A", "D", "C", "B", "B", "A", "A", "C",
        "を", "理解し", "違え", "に", "少なく", "向け", "支", "残り", "の", "えら",
    ]
    return {idx + 1: val for idx, val in enumerate(vals)}


def henan_verified_answers() -> dict[int, str]:
    vals = [
        "C", "B", "B", "A", "C", "B", "A", "B", "A", "B",
        "A", "C", "B", "A", "B", "A", "C", "B", "C", "A",
        "D", "A", "B", "C", "B", "B", "D", "C", "A", "B",
        "A", "C", "D", "A", "B", "B", "A", "C", "D", "C",
        "C", "D", "B", "B", "C", "A", "D", "A", "D", "B",
        "に", "と", "冷静に", "連れて", "よかっ", "入り", "戦争", "され", "できごと", "の",
    ]
    return {idx + 1: val for idx, val in enumerate(vals)}


def split_pages(dir_name: str) -> list[dict]:
    d = ROOT / dir_name
    files = sorted(d.glob("page-*.txt"), key=lambda p: int(re.search(r"page-(\d+)", p.stem).group(1)))
    return [{"page": idx + 1, "text": read(p), "image": f"{dir_name}/{p.stem}.png"} for idx, p in enumerate(files)]


def pages_from_docx_text(text_path: Path, fallback_pages: list[dict]) -> list[dict]:
    text = read(text_path)
    if not text.strip():
        return fallback_pages
    chunks = re.split(r"(?=日语试题\s*第\d+页\(共\d+页\))", text)
    pages: list[dict] = []
    for idx, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        image = fallback_pages[min(idx, len(fallback_pages) - 1)]["image"] if fallback_pages else ""
        pages.append({"page": len(pages) + 1, "text": chunk.strip(), "image": image})
    return pages or [{"page": 1, "text": text, "image": fallback_pages[0]["image"] if fallback_pages else ""}]


def clean_henan_docx_text(text: str) -> str:
    """Fix the Word export's two-column reading section order for the Henan paper."""
    if "金太阳" in text:
        text = text.replace("金太阳", "")
    start = text.find("第二部分阅读理解")
    fourth = text.find("(四)", start)
    if start < 0 or fourth < 0:
        return text
    section = """第二部分阅读理解(共20小题：每小题2.5分，满分50分)
阅读下列短文，从A、B、C、D四个选项中选出符合文章内容的最佳选项，并在答题卡上将该项涂黑。
(一)
私たちの生活を便利で快適にしてくれるプラスチックですが、多くは自然に分解されないという課題があります。プラスチックは悪いものというイメージを持つ人が多いかもしれません。しかし、いまさらまったく使わない生活は考えられません。プラスチックとの共生を考えることが大切です。
プラスチックのリサイクルも進んでいますが、最終的にはゴミとなり、焼かれることで二酸化炭素が発生します。(ア)、近年増えているのが、石油のかわりにサトウキビやトウモロコシ(甘蔗和玉米)といった植物を使った「バイオマスプラスチック」です。レジ袋の場合はサトウキビを原料としてエタノール(乙醇)を取り出し、エチレン(乙烯)を作ります。
エチレンからポリエチレンにするのは、石油と同じ手順です。自然の中で分解される「生分解性プラスチック」もあります。土の中の微生物がプラスチックを分解してくれて、最後は二酸化炭素と水になります。
使ったプラスチックを化学的に分解してナフサ(粗汽油)に戻し、再び材料として利用するリサイクルについても研究が進んでいます。
21. 文中の「課題」に対して、どうすべきか。
A. 分解できる材料で作られた製品を多めに生産すべきだ。
B. 分解されないプラスチックの使用を禁止すべきだ。
C. プラスチックの悪さをもう一度見直すべきだ。
D. プラスチックとどう共生できるか考えるべきだ。
22. 文中の(ア)に入れるのに最も適当なものはどれか。
A. そこで B. それに C. そうしたら D. そのように
23. 「バイオマスプラスチック」の製品として、正しいのはどれか。
A. ガソリンから取り出した物質で作られたゴム手袋
B. トウモロコシから取り出した物質で作られた食器
C. 石油から取り出した物質で作られたレジ袋
D. ナフサから取り出した物質で作られた包装資材
24. 「生分解性プラスチック」はどんなプラスチックか。
A. 植物から取り出した化学的な物質を使い、合成されるプラスチック
B. 化学的に分解でき、そしてもう一度リサイクルできるプラスチック
C. 土の中の微生物が分解でき、最後は二酸化炭素と水になるプラスチック
D. 自然の微生物に分解され、植物の栄養として吸収されるプラスチック
25. また研究が続いているのは何か。
A. 地球にある再生可能な天然資源を探し、開発すること
B. プラスチックを化学的に分解してナフサに戻し、再利用すること
C. バイオマスプラスチックを作るに使える植物の種類を増やすこと
D. 使われているプラスチックを合成する手順を簡易化させること
(二)
寒い季節に、虫がなかなか見られなくなります。少し寂しいですが、寒い時だけに出てくる虫もいます。冬に一番よく見られるのは、冬尺という小さな蛾の仲間です。幼虫が尺取虫なので、尺蛾と呼ばれ、その中の一部が冬に現れるのです。
冬尺は秋遅くから、春になる前の寒い時期に出てきます。木の葉が落ちた森で、暖かい日に、ひらひらと飛ぶ様子が見られます。おもしろいのは、雌は飛ぶのが苦手なものが多いことです。なかには、羽がなくなって、まったく飛べなくなったものもいます。そういうものは、山の中の手すりや、木の枝を見て回って探してみましょう。また、寒い時期にずっといるわけではなく、種によって出る時期は決まっています。なかなか探すのは難しいかもしれませんが、この時期の暖かい日に山を歩いて探してみると楽しいと思います。
(ア)、元気になるのは春や夏でも、成虫で冬を越す虫もいます。例えば、ホソミオツネントンボ(細身越冬蜻蜓)はそういう昆虫です。普段は水辺にいますが、この時期は森の中で過ごし、暖かい日に飛ぶのが見られます。枯れ枝のように目立たない色をしています。
また、キクテハやアカテハ(木叶蝶和赤蛱蝶)などの蝶も成虫で冬を越し、暖かい日には飛ぶこともあります。そのほか、蠅などの小さい虫にも、冬を好んで飛び回るものがいます。昆虫というのはいろいろ暮らし方で生きるものがいて、冬にも元気にしているものがいるというのは本当にびっくりです。
26. 冬尺はいつ出てくるか。
A. 初春から初秋までの暑い時期
B. 深秋から春の前までの寒い時期
C. 真冬から初春までの暖かい時期
D. 真夏から真冬までの長い時期
27. 文中の「そういうもの」の指すものは何か。
A. 飛ぶのが苦手だが、ひらひらと飛べる雄の冬尺
B. 飛ぶのが苦手だが、ひらひらと飛べる雌の冬尺
C. 羽がなく、ぜんぜん飛べなくなった雄の冬尺
D. 羽がなく、ぜんぜん飛べなくなった雌の冬尺
28. 文中の(ア)に入れるのに最も適当なのはどれか。
A. そのため B. そのように C. そのほか D. そのうえに
29. 文中に「そういう昆虫」とあるが、どんな昆虫か。
A. 成虫で冬を越す虫
B. 幼虫で水の中に生きる虫
C. 成虫で水辺で暮らす虫
D. 幼虫で森の中で過ごす虫
30. 文章の内容に合っているのはどれか。
A. 寒い時に出てくる昆虫の種類は少ないが、量はほかの季節より多い。
B. 寒い時期の暖かい日に森に行くと、冬に出る昆虫を見る可能性がある。
C. 寒い時に出てくる昆虫はだいたい同じ時期に出て、探すのも簡単だ。
D. 寒い時期に成虫で活躍している昆虫がいるのは筆者にとって珍しくない。
(三)
川根由美子さん(67歳)が今年2月に受け取った段ボール箱には、自費出版した小説200冊が入っていました。福祉の仕事をしながら文章を書き続けてきた彼女は、自信がなかったため、「誰も読まない」と言われるのを恐れていたそうです。(ア)表紙にはこだわり、砂浜の絵と大好きなカキツバタの青い色で和なデザインにしました。同人誌仲間から良い反応をもらえたことで、本にしてよかったと思えるようになりました。
自費出版とは著者の思いを凝縮したものですが、多くの場合、それが広く読まれることなく消えてしまうことがあります。そこで、川根さんは5月に自宅で「本屋」を始めました。この本屋は利益を考えず、作者同士が交流できる場を指しています。訪れる人は少ないもの、自分の本も置いてほしいという希望者がおり、一生に一度だけでも形として残したいという意気込みが感じられます。「活字によって生き様を残す」という想いが伝わってくると言います。
この店には多種多様な自費出版物があります。例えば街の電器屋さんによる郷土史研究にもとづいた時代小説や、30年越しにあぜ道についての研究書などがあります。本を見ただけでも楽しいですが、その背後にある執筆者それぞれの背景やストーリーを知れば、一層その魅力が増します。
店名「旅する本屋ラボール」には、自費出版された本たちが見知らぬ誰かへ渡り、「どこか遠くへと旅してほしい」という願いが込められています。このような活動が、小さなコミュニティ内外で新たなつながりや発見を生み出すことにつながっています。
31. 文中の(ア)に入れるのに最も適当なものはどれか。
A. それでも B. そのため C. しかも D. ところで
32. 川根さんが始めた「本屋」の目的として、最も適当なものはどれか。
A. 自費出版物を広く販売して利益を上げること
B. 郷土史や研究書などの本を収集して展示すること
C. 作者同士が交流できる場を提供すること
D. 活字で書かれた本をデジタル化し保存すること
33. 文中の「意気込み」を最も正しく表すものはどれか。
A. 将来を考えた冷静な決断
B. すぐに結果を出すための努力
C. ビジネスとして成功させたいという考え
D. 自分の本を世に出したいという強い思い
34. 文中の「旅する本屋ラボール」の店名に込められた願いは何か。
A. 自費出版された本が見知らぬ人の手に渡ることを願う。
B. 多くの人が本を通じて旅行に出かけることを願う。
C. 作者が自分の本を持って各地を旅することを願う。
D. 小さなコミュニティの外に本屋を広げることを願う。
35. この文章の内容と合っているものはどれか。
A. 川根さんは最初から自費出版に自信を持っていた。
B. 自費出版物には、作者の経験や思いが反映されている。
C. この本屋は訪れる人が多く、常ににぎわっている。
D. この本屋では、利益を上げるための販売戦略を行っている。
"""
    return text[:start] + section + "\n" + text[fourth:]


def pages_from_henan_docx_text(text_path: Path, fallback_pages: list[dict]) -> list[dict]:
    pages = pages_from_docx_text(text_path, fallback_pages)
    for page in pages:
        page["text"] = clean_henan_docx_text(page["text"])
    return pages


def split_questions(raw_pages: list[dict]) -> dict[int, dict]:
    text = "\n".join(p["text"] for p in raw_pages)
    text = normalize_text(text)
    # 只切题号开头，保留选项和题干。OCR 可能有少量误字，但题号绑定以后不依赖题号猜答案。
    start = text.find("第一部分")
    if start >= 0:
        text = text[start:]
    markers = [
        (int(m.group(1)), m.start())
        for m in re.finditer(r"(?m)^\s*([1-5]?\d|60)\s*[.、]\s*", text)
    ]
    cleaned = []
    seen = set()
    for n, pos in markers:
        if 1 <= n <= 60 and n not in seen:
            cleaned.append((n, pos))
            seen.add(n)
    questions: dict[int, dict] = {}
    for idx, (n, pos) in enumerate(cleaned):
        end = cleaned[idx + 1][1] if idx + 1 < len(cleaned) else len(text)
        block = text[pos:end].strip()
        if len(block) < 8:
            continue
        questions[n] = {"number": n, "body": block}
    # Attach shared passages to the first question in each reading/language group.
    pos_by_no = {n: pos for n, pos in cleaned}

    def prepend_passage(qno: int, marker: str, prev_qno: int | None = None) -> None:
        if qno not in questions or qno not in pos_by_no:
            return
        start = text.rfind(marker, 0, pos_by_no[qno])
        if start < 0:
            return
        if prev_qno and prev_qno in pos_by_no:
            start = max(start, pos_by_no[prev_qno])
        passage = text[start:pos_by_no[qno]].strip()
        if passage and passage not in questions[qno]["body"]:
            questions[qno]["body"] = passage + "\n\n" + questions[qno]["body"]

    prepend_passage(21, "(一)", 20)
    prepend_passage(26, "(二)", 25)
    prepend_passage(31, "(三)", 30)
    prepend_passage(36, "(四)", 35)
    if 41 in questions and 41 in pos_by_no:
        third = text.rfind("第三部分", 0, pos_by_no[41])
        base = third if third >= 0 else 0
        starts = [p for p in [text.find("僕は", base, pos_by_no[41]), text.find("寒さが増す", base, pos_by_no[41])] if p >= 0]
        start = min(starts) if starts else -1
        if start >= 0:
            passage = text[start:pos_by_no[41]].strip()
            questions[41]["body"] = passage + "\n\n" + questions[41]["body"]

    cloze_starts = [p for p in [text.find("言葉は、人と人"), text.find("卒業生の皆さん")] if p >= 0]
    cloze_start = min(cloze_starts) if cloze_starts else -1
    cloze_end = text.find("第四部分", cloze_start)
    if cloze_start >= 0:
        cloze = text[cloze_start: cloze_end if cloze_end > cloze_start else len(text)].strip()
        for n in range(51, 61):
            if n in questions:
                questions[n]["body"] = cloze + f"\n\n第 {n} 空"
            else:
                questions[n] = {"number": n, "body": cloze + f"\n\n第 {n} 空"}
    for n, marker in [(20, "第二部分"), (25, "(二)"), (30, "(三)"), (35, "(四)"), (40, "第三部分")]:
        if n in questions:
            cut = questions[n]["body"].find(marker)
            if cut > 0:
                questions[n]["body"] = questions[n]["body"][:cut].strip()
    return questions


def grammar_notes() -> list[dict]:
    return [
        {"jp": "ため", "kana": "ため", "cn": "原因/目的。阅读中要看前后句判断“因为”还是“为了”。"},
        {"jp": "ように", "kana": "ように", "cn": "目的、样态或比喻。接可能/ない形时常表示目的。"},
        {"jp": "によって", "kana": "によって", "cn": "依据、手段、原因，或随对象变化。"},
        {"jp": "にとって", "kana": "にとって", "cn": "对……来说，后面多接评价判断。"},
        {"jp": "として", "kana": "として", "cn": "作为……，表示身份、资格、立场。"},
        {"jp": "だけでなく", "kana": "だけでなく", "cn": "不仅……而且……，常与「も」呼应。"},
        {"jp": "わけではない", "kana": "わけではない", "cn": "并不是……，部分否定。"},
        {"jp": "かもしれない", "kana": "かもしれない", "cn": "也许/可能，表示不确定推量。"},
        {"jp": "ことがある", "kana": "ことがある", "cn": "有时会……；「たことがある」表示经历。"},
        {"jp": "てしまう", "kana": "てしまう", "cn": "完成、遗憾、失误或不可控结果。"},
        {"jp": "てくれる", "kana": "てくれる", "cn": "别人为我方做，或某事给我方带来益处。"},
        {"jp": "ながら", "kana": "ながら", "cn": "一边……一边……；也可表示逆接。"},
        {"jp": "ば", "kana": "ば", "cn": "条件形，如果……。"},
        {"jp": "ても", "kana": "ても", "cn": "即使……也……。"},
        {"jp": "思いがち", "kana": "おもいがち", "cn": "「动词ます形/名词 + がち」表示容易出现某种倾向，多用于负面或偏向性的状态；「思いがち」就是“容易以为/往往认为”。"},
        {"jp": "とは限らない", "kana": "とはかぎらない", "cn": "表示“不一定……/未必……”。常用于纠正绝对化判断，如「理解できているとは限らない」= 未必真的理解了。"},
        {"jp": "読み取る", "kana": "よみとる", "cn": "复合动词，表示从文字、表情、背景等信息中“读出、领会、理解”。阅读题中常指把隐含信息理解出来。"},
        {"jp": "余裕がなくなり", "kana": "よゆうがなくなり", "cn": "「余裕がある/ない」表示有/没有从容、余地；「なくなり」表示变化成没有，句中指“变得没有余力/从容”。"},
        {"jp": "見落として", "kana": "みおとして", "cn": "「見落とす」表示看漏、忽略。本句常用于说明因为先入为主而忽略关键内容。"},
        {"jp": "受け止める", "kana": "うけとめる", "cn": "复合动词。「受ける」+「止める」，原义是接住、挡住；抽象用法表示“认真接受、理解、消化”对方的话或情绪。"},
        {"jp": "受け止め", "kana": "うけとめ", "cn": "「受け止める」的连用形。句中「より深く受け止める」表示更深入地理解、接纳对方的话。"},
        {"jp": "引き出す", "kana": "ひきだす", "cn": "复合动词。「引く」+「出す」，表示拉出来、引出；抽象用法表示把能力、反应、想法等激发出来。"},
        {"jp": "思い込む", "kana": "おもいこむ", "cn": "复合动词。「思う」+「込む」，表示深信、认定、想当然地以为。常带有主观判断过强的语感。"},
        {"jp": "思い込むこと", "kana": "おもいこむこと", "cn": "名词化表达，表示“认定这件事/想当然地以为”。阅读中常用于指出错误认知。"},
        {"jp": "汲み取る", "kana": "くみとる", "cn": "复合动词。原义是舀取水；抽象用法表示体会、理解、领会对方的心情或意图。"},
        {"jp": "汲み取れて", "kana": "くみとれて", "cn": "「汲み取る」的可能形「汲み取れる」接て形，表示“能够领会/能够体会”。否定常见为「汲み取れていない」。"},
        {"jp": "見直す", "kana": "みなおす", "cn": "复合动词。「見る」+「直す」，表示重新看、重新审视、重新评价。文中「状態を見直す」= 重新审视自己的状态。"},
        {"jp": "見直すこと", "kana": "みなおすこと", "cn": "把「見直す」名词化，表示“重新审视这件事”。常作主语或宾语。"},
        {"jp": "つもり", "kana": "つもり", "cn": "用法1：表示打算、计划，如「行くつもりだ」= 打算去。用法2：表示自以为、自己认为，如「聞けているつもり」= 自以为听懂了。阅读中常考第二种。"},
        {"jp": "聞けているつもり", "kana": "きけているつもり", "cn": "「动词可能形ている + つもり」表示“自以为已经能……”。这里指自以为已经听懂，但实际可能没有真正理解。"},
        {"jp": "あちこち", "kana": "あちこち", "cn": "副词/代词，表示“到处、这儿那儿”。文中「あちこちで聞こえる」= 到处都能听到。"},
        {"jp": "目が覚める", "kana": "めがさめる", "cn": "惯用表达，表示“醒来、清醒过来”。也可用于比喻突然醒悟。"},
        {"jp": "目が覚め", "kana": "めがさめ", "cn": "「目が覚める」的连用形。文中「静電気で目が覚める」表示因为静电而醒来。"},
        {"jp": "思わず", "kana": "おもわず", "cn": "副词，表示“不由得、禁不住”。强调不是有意识地做，而是自然反应。"},
        {"jp": "出来事", "kana": "できごと", "cn": "名词，表示“事件、事情”。常指生活中发生的一件事。"},
        {"jp": "たびに", "kana": "たびに", "cn": "接动词辞书形或名词+の，表示“每当……就……”。如「上着を脱ぐたびに」= 每次脱外套时。"},
        {"jp": "軽く跳ね", "kana": "かるくはね", "cn": "「軽く」表示轻轻地、稍微；「跳ねる」表示跳起、弹起。文中指粉笔灰轻轻弹起。"},
        {"jp": "跳ね", "kana": "はね", "cn": "「跳ねる」的连用形，表示跳起、弹起、飞溅。"},
        {"jp": "かえって", "kana": "かえって", "cn": "副词，表示“反而、却”。用于结果与预想相反的情况。"},
        {"jp": "ぼそっと", "kana": "ぼそっと", "cn": "拟态副词，表示小声嘟囔、低声说话的样子。"},
        {"jp": "ぱっと", "kana": "ぱっと", "cn": "拟态副词，表示突然、一下子、迅速明亮起来。文中「ぱっと明るくなる」指气氛一下子明朗。"},
        {"jp": "くだらない", "kana": "くだらない", "cn": "形容词，表示无聊的、无价值的、不正经的。文中「くだらない冗談」是轻松的小玩笑。"},
        {"jp": "思い出して", "kana": "おもいだして", "cn": "「思い出す」的て形，表示想起、回忆起。"},
        {"jp": "思い出し", "kana": "おもいだし", "cn": "「思い出す」的连用形，表示想起、回忆。"},
        {"jp": "むしろ", "kana": "むしろ", "cn": "副词，表示“倒不如说、反而”。用于提出与前面预期不同或更合适的判断。"},
        {"jp": "心当たり", "kana": "こころあたり", "cn": "名词，表示“线索、头绪、想得到的相关情况”。「心当たりの方」= 有线索/知道情况的人。"},
        {"jp": "見入った", "kana": "みいった", "cn": "「見入る」的た形，表示看得入神、凝视。文中指被便条内容吸引而仔细看。"},
        {"jp": "わけではない", "kana": "わけではない", "cn": "表示“不一定……/并不是……”。「必ず持ち主が見つかるわけではない」= 并不一定能找到失主。"},
        {"jp": "当たり前", "kana": "あたりまえ", "cn": "名词/な形容词，表示理所当然、普通、应该如此。文中指很多人把拾物上交视作理所当然。"},
        {"jp": "しばらく", "kana": "しばらく", "cn": "副词，表示一会儿、暂时、片刻。文中「しばらく迷っていた」= 犹豫了一会儿。"},
        {"jp": "歩き出した", "kana": "あるきだした", "cn": "复合动词「歩く+出す」的过去形，表示开始走、迈步走出。"},
        {"jp": "思いやる", "kana": "おもいやる", "cn": "动词，表示体谅、关怀、替别人着想。文中「見えない他人を思いやる」= 体谅看不见的他人。"},
        {"jp": "さえ", "kana": "さえ", "cn": "副助词，表示“连……都”或最低条件；在「自分さえ良ければ」中表示“只要自己好就行”。"},
        {"jp": "自分さえ良ければ", "kana": "じぶんさえよければ", "cn": "固定感很强的表达，表示“只要自己方便/自己好就行”，带有自私、只顾自己的语气。"},
        {"jp": "目立ち始めている", "kana": "めだちはじめている", "cn": "复合表达「动词ます形+始める」表示开始……；「ている」表示这种趋势正在持续。即“开始变得显眼/突出”。"},
        {"jp": "炎上につながる", "kana": "えんじょうにつながる", "cn": "「炎上」指网络上批评集中、舆论爆发；「につながる」表示导致、引发。即“引发舆论争议”。"},
        {"jp": "見つめ直す", "kana": "みつめなおす", "cn": "复合动词，表示重新凝视、重新审视。比「見直す」更强调认真面对自身行为或问题。"},
        {"jp": "上り切る", "kana": "のぼりきる", "cn": "复合动词。「切る」作补助动词表示彻底完成；「上り切る」= 完全登上、走到楼梯顶。"},
        {"jp": "上り切るころ", "kana": "のぼりきるころ", "cn": "表示“快/刚走到顶的时候”。「ころ」表示大致时间点。"},
        {"jp": "振り返った", "kana": "ふりかえった", "cn": "「振り返る」的过去形，表示回头看；也可表示回顾。文中是再次回头看便条。"},
        {"jp": "名もなき", "kana": "なもなき", "cn": "连体表达，表示无名的、不知名的。文中「名もなき善意」= 无名的善意。"},
        {"jp": "よみがえる", "kana": "よみがえる", "cn": "动词，表示复苏、重新浮现。用于记忆时表示“回想起来、浮现在脑海中”。"},
        {"jp": "受け入れ", "kana": "うけいれ", "cn": "「受け入れる」的连用形/名词化，表示接受、接纳。文中「広く受け入れられた」= 被广泛接受。"},
        {"jp": "受け入れられた", "kana": "うけいれられた", "cn": "「受け入れる」的被动态过去形，表示“被接受了”。"},
        {"jp": "によれば", "kana": "によれば", "cn": "表示信息来源或判断依据，“据……说/根据……”。常用于引用专家、资料、报道。"},
        {"jp": "落ち着き", "kana": "おちつき", "cn": "名词，表示安定、平静、沉稳。文中「落ち着きを与える」= 给人安定感。"},
        {"jp": "てしまう", "kana": "てしまう", "cn": "表示动作完成、遗憾结果或不由自主发生；如「優先してしまう」带有“无意中就优先了”的语感。"},
        {"jp": "ようになる", "kana": "ようになる", "cn": "表示状态变化，“变得会……/开始……”。常接动词基本形或可能形。"},
        {"jp": "なければならない", "kana": "なければならない", "cn": "必须……。由否定条件构成，语气较正式。"},
        {"jp": "こそ", "kana": "こそ", "cn": "强调助词，“正是……才……”。用于突出关键对象或原因。"},
        {"jp": "ほど", "kana": "ほど", "cn": "表示程度，“到……程度”；也可构成「AほどB」比较句。"},
    ]


def furigana_pairs() -> list[list[str]]:
    return [
        ["円滑", "えんかつ"], ["錯覚", "さっかく"], ["価値観", "かちかん"], ["無意識", "むいしき"],
        ["静電気", "せいでんき"], ["乾燥", "かんそう"], ["衝突", "しょうとつ"], ["雰囲気", "ふんいき"],
        ["想像力", "そうぞうりょく"], ["公共空間", "こうきょうくうかん"], ["善意", "ぜんい"],
        ["香り", "かおり"], ["嗅覚", "きゅうかく"], ["大脳辺縁系", "だいのうへんえんけい"], ["自律神経", "じりつしんけい"],
        ["言葉", "ことば"], ["距離", "きょり"], ["感謝", "かんしゃ"], ["励まし", "はげまし"], ["責任", "せきにん"],
        ["星空", "ほしぞら"], ["節電", "せつでん"], ["個性", "こせい"], ["内面", "ないめん"],
        ["馬", "うま"], ["冷静", "れいせい"], ["戦争", "せんそう"], ["徴兵", "ちょうへい"], ["現金", "げんきん"],
    ]


def ruby_html(text: str) -> str:
    try:
        import pykakasi
    except Exception:
        return ""
    kks = pykakasi.kakasi()
    overrides = {
        "遮って": "さえぎって",
        "驚く": "おどろく",
        "驚 く": "おどろく",
        "受け止める": "うけとめる",
        "受け止め": "うけとめ",
        "引き出す": "ひきだす",
        "思い込む": "おもいこむ",
        "思い込むこと": "おもいこむこと",
        "汲み取れて": "くみとれて",
        "汲み取る": "くみとる",
        "見直す": "みなおす",
        "見直すこと": "みなおすこと",
        "見落として": "みおとして",
        "読み取る": "よみとる",
        "目が覚める": "めがさめる",
        "目が覚め": "めがさめ",
        "出来事": "できごと",
        "軽く": "かるく",
        "跳ね": "はね",
        "思い出して": "おもいだして",
        "思い出し": "おもいだし",
        "心当たり": "こころあたり",
        "見入った": "みいった",
        "当たり前": "あたりまえ",
        "歩き出した": "あるきだした",
        "思いやる": "おもいやる",
        "自分さえ良ければ": "じぶんさえよければ",
        "目立ち始めている": "めだちはじめている",
        "炎上につながる": "えんじょうにつながる",
        "見つめ直す": "みつめなおす",
        "上り切るころ": "のぼりきるころ",
        "上り切る": "のぼりきる",
        "振り返った": "ふりかえった",
        "名もなき": "なもなき",
        "匂い": "におい",
        "よみがえる": "よみがえる",
        "受け入れられた": "うけいれられた",
        "受け入れ": "うけいれ",
        "落ち着き": "おちつき",
        "五感": "ごかん",
        "嗅覚": "きゅうかく",
        "大脳辺縁系": "だいのうへんえんけい",
    }
    placeholders: dict[str, str] = {}
    protected = text
    for idx, (word, reading) in enumerate(sorted(overrides.items(), key=lambda x: len(x[0]), reverse=True)):
        if word not in protected:
            continue
        token = f"__RUBYOVERRIDE{idx}__"
        protected = protected.replace(word, token)
        clean_word = word.replace(" ", "")
        placeholders[token] = f"<ruby>{clean_word}<rt>{reading}</rt></ruby>"

    parts: list[str] = []
    for item in kks.convert(protected):
        orig = item.get("orig", "")
        hira = item.get("hira", "")
        if orig in placeholders:
            parts.append(placeholders[orig])
            continue
        if re.search(r"[一-龯々]", orig) and hira and hira != orig:
            parts.append(f"<ruby>{orig}<rt>{hira}</rt></ruby>")
        else:
            parts.append(orig)
    return "".join(parts)


def strip_to_translate(text: str, max_chars: int = 1800) -> str:
    text = re.sub(r"日语试题\s*第\d+页\(共\d+页\)", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def load_translate_cache() -> dict[str, str]:
    if not TRANSLATE_CACHE.exists():
        return {}
    try:
        return json.loads(TRANSLATE_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_translate_cache(cache: dict[str, str]) -> None:
    TRANSLATE_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def translate_ja_to_cn(text: str, cache: dict[str, str]) -> str:
    src = strip_to_translate(text)
    if not src:
        return ""
    if src in cache and cache[src]:
        return cache[src]
    url = (
        "https://translate.googleapis.com/translate_a/single?client=gtx&sl=ja&tl=zh-CN&dt=t&q="
        + urllib.parse.quote(src)
    )
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=15).read().decode("utf-8"))
        cn = "".join(part[0] for part in data[0] if part and part[0]).strip()
    except Exception:
        cn = ""
    cache[src] = cn
    time.sleep(0.12)
    return cn


def build():
    translate_cache = load_translate_cache()
    gd_answers = guangdong_verified_answers()
    hn_answers = henan_verified_answers()
    validate_answers("广东预测卷", gd_answers)
    validate_answers("河南联考", hn_answers)

    gd_pdf_pages = split_pages("ocr_pages")
    gd_pages = pages_from_docx_text(ROOT / "rebuild" / "guangdong_docx.txt", gd_pdf_pages)
    hn_pdf_pages = split_pages("henan_ocr_pages")
    hn_pages = pages_from_henan_docx_text(ROOT / "rebuild" / "henan_docx.txt", hn_pdf_pages)
    exams = [
        {
            "id": "guangdong",
            "title": "广东省全国统一考试预测卷",
            "pages": gd_pages,
            "paperPages": gd_pdf_pages,
            "answers": gd_answers,
            "answerText": "\n".join(read(p) for p in sorted((ROOT / "answer_ocr_pages").glob("page-*.txt"))),
        },
        {
            "id": "henan",
            "title": "金太阳·河南2026届高三5月联考",
            "pages": hn_pages,
            "paperPages": hn_pdf_pages,
            "answers": hn_answers,
            "answerText": read(ROOT / "henan_answers_extracted.txt"),
        },
    ]
    for exam in exams:
        qs = split_questions(exam["pages"])
        exam["questions"] = [
            {
                "number": i,
                "answer": exam["answers"][i],
                "body": qs.get(i, {"body": "（该题 OCR 文本需人工校对，请参照原卷图片。）"})["body"],
            }
            for i in range(1, 61)
        ]
        for q in exam["questions"]:
            q["ruby_html"] = ruby_html(q["body"])
            q["translation_cn"] = translate_ja_to_cn(q["body"], translate_cache)
    save_translate_cache(translate_cache)

    payload = {
        "exams": exams,
        "grammarNotes": grammar_notes(),
        "furigana": furigana_pairs(),
    }
    (OUT / "exam_data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_html(payload)
    return payload


def write_html(payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False)
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>日语双卷题目解析</title>
  <link rel="stylesheet" href="web_assets/base-style.css">
  <style>
    body {{ background:#f6f8fb; color:#1f2937; }}
    .navbar {{ height:56px; }}
    .shell {{ display:grid; grid-template-columns:260px minmax(0,1fr); height:calc(100vh - 56px); overflow:hidden; transition:grid-template-columns .2s ease; }}
    .shell.nav-collapsed {{ grid-template-columns:54px minmax(0,1fr); }}
    .side {{ background:#151335; color:#e0e7ff; padding:14px; overflow:auto; }}
    .nav-toggle {{ width:100%; border:1px solid #37306b; background:#312e81; color:white; border-radius:8px; padding:9px 6px; margin-bottom:12px; cursor:pointer; font-weight:800; }}
    .shell.nav-collapsed .side {{ padding:10px 8px; overflow:hidden; }}
    .shell.nav-collapsed .side-content {{ display:none; }}
    .shell.nav-collapsed .nav-toggle {{ writing-mode:vertical-rl; min-height:92px; padding:8px 4px; }}
    .main {{ overflow:auto; }}
    .exam-tab,.qbtn {{ width:100%; border:1px solid #37306b; background:#1e1b4b; color:#c7d2fe; border-radius:8px; padding:9px; margin-bottom:8px; cursor:pointer; text-align:left; }}
    .exam-tab.active,.qbtn.active {{ background:#4f46e5; color:white; border-color:#818cf8; }}
    .qgrid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:6px; }}
    .qbtn {{ text-align:center; margin:0; padding:7px 0; font-weight:700; }}
    .hero {{ background:white; border-bottom:1px solid #e5e7eb; padding:16px 20px; display:flex; justify-content:space-between; gap:12px; align-items:center; }}
    .hero h1 {{ margin:0; font-size:22px; }}
    .tabs {{ display:flex; gap:8px; flex-wrap:wrap; }}
    .tab {{ border:1px solid #c7d2fe; background:#eef2ff; color:#3730a3; border-radius:8px; padding:8px 12px; font-weight:700; cursor:pointer; }}
    .tab.active {{ background:#4f46e5; color:white; }}
    .grid {{ display:grid; grid-template-columns:minmax(360px,.9fr) minmax(440px,1.1fr); gap:14px; padding:14px; align-items:start; }}
    .panel {{ background:white; border:1px solid #e5e7eb; border-radius:10px; box-shadow:var(--shadow); overflow:hidden; }}
    .head {{ padding:12px 14px; border-bottom:1px solid #e5e7eb; display:flex; justify-content:space-between; gap:10px; align-items:center; }}
    .head h2 {{ margin:0; font-size:16px; }}
    .body {{ padding:14px; }}
    .paper {{ width:100%; border:1px solid #e5e7eb; border-radius:8px; display:block; }}
    .paper-scroll {{ max-height:calc(62vh - 120px); overflow-y:auto; display:grid; gap:12px; padding-right:6px; }}
    .paper-page-label {{ font-size:12px; color:#64748b; font-weight:700; margin:2px 0 -6px; }}
    .right-stack {{ display:grid; gap:14px; }}
    .grammar-list {{ display:grid; gap:10px; }}
    .grammar-scroll {{ max-height:260px; overflow-y:auto; padding-right:6px; }}
    .grammar-item {{ border-left:4px solid #f97316; background:#fff7ed; border-radius:8px; padding:10px 12px; }}
    .grammar-item b {{ color:#9a3412; }}
    .jp {{ white-space:pre-wrap; font-family:var(--font-jp); font-size:15px; line-height:1.85; }}
    ruby rt {{ color:#4f46e5; font-size:.66em; font-weight:700; }}
    .grammar {{ background:#fff7ed; border-bottom:2px solid #fb923c; color:#9a3412; border-radius:4px; padding:0 2px; font-weight:700; }}
    .answer {{ display:inline-flex; align-items:center; gap:8px; background:#ecfdf5; border:1px solid #a7f3d0; color:#047857; padding:8px 10px; border-radius:8px; font-weight:800; }}
    .answers {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(72px,1fr)); gap:8px; }}
    .note {{ border-left:4px solid #4f46e5; background:#eef2ff; padding:10px 12px; border-radius:8px; margin-bottom:10px; }}
    .warn {{ background:#fffbeb; border:1px solid #fde68a; color:#92400e; border-radius:8px; padding:10px 12px; margin-bottom:12px; }}
    .hidden {{ display:none!important; }}
    @media (max-width:900px) {{ .shell,.shell.nav-collapsed{{grid-template-columns:1fr;height:auto;overflow:visible}} .shell.nav-collapsed .side-content{{display:block}} .shell.nav-collapsed .nav-toggle{{writing-mode:horizontal-tb;min-height:0}} .grid{{grid-template-columns:1fr}} .hero{{align-items:flex-start;flex-direction:column}} }}
  </style>
</head>
<body>
  <nav class="navbar"><div class="nav-brand">高考日语双卷解析</div><div class="nav-center" id="navTitle"></div><div class="nav-links"><span class="nav-link active">60题答案已校验</span></div></nav>
  <div class="shell" id="shell">
    <aside class="side">
      <button class="nav-toggle" id="navToggle" type="button">隐藏题号</button>
      <div class="side-content">
        <div style="font-weight:800;margin:0 0 8px">试卷切换</div>
        <div id="examTabs"></div>
        <div style="font-weight:800;margin:16px 0 8px">题号导航</div>
        <div class="qgrid" id="qnav"></div>
      </div>
    </aside>
    <main class="main">
      <section class="hero">
        <div><h1 id="title"></h1><div id="sub" style="color:#64748b;font-size:13px;margin-top:4px"></div></div>
        <div class="tabs">
          <button class="tab active" data-view="question">题目+答案</button>
          <button class="tab" data-view="paper">原卷对照</button>
          <button class="tab" data-view="answers">答案解析</button>
          <button class="tab" data-view="grammar">语法重点</button>
        </div>
      </section>
      <section class="grid" id="questionView">
        <div class="panel"><div class="head"><h2 id="qTitle"></h2><span class="answer" id="qAnswer"></span></div><div class="body"><div class="jp" id="qBody"></div><div class="note" style="margin-top:12px"><b>中文翻译</b><br><span id="qCn"></span></div></div></div>
        <div class="right-stack">
          <div class="panel"><div class="head"><h2>原卷连续对照</h2><span id="pageLabel">可滚动查看整卷</span></div><div class="body"><div class="paper-scroll" id="paperScroller"></div></div></div>
          <div class="panel"><div class="head"><h2>当前题语法解析</h2><span>自动匹配重点表达</span></div><div class="body grammar-scroll"><div class="grammar-list" id="currentGrammar"></div></div></div>
        </div>
      </section>
      <section class="grid hidden" id="paperView"></section>
      <section class="grid hidden" id="answersView"></section>
      <section class="grid hidden" id="grammarView"></section>
    </main>
  </div>
  <script>
    const DATA = __DATA__;
    let exam = DATA.exams[0], qno = 1;
    const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
    function mark(s) {{
      let out = esc(s);
      DATA.furigana.forEach(([w,k]) => out = out.replaceAll(esc(w), `<ruby>${esc(w)}<rt>${esc(k)}</rt></ruby>`));
      DATA.grammarNotes.forEach(n => out = out.replaceAll(esc(n.jp), `<span class="grammar" title="${esc(n.cn)}">${esc(n.jp)}</span>`));
      return out;
    }}
    function qPage(n) {{
      const approx = Math.max(1, Math.min(exam.pages.length, Math.ceil(n / (exam.id === 'henan' ? 15 : 6))));
      return exam.pages[approx - 1] || exam.pages[0];
    }}
    function renderShell() {{
      navTitle.textContent = exam.title; title.textContent = exam.title; sub.textContent = '共60题；答案表完整校验；阅读文本已做假名标注和语法高亮。';
      examTabs.innerHTML = DATA.exams.map(e => `<button class="exam-tab ${e.id===exam.id?'active':''}" data-exam="${e.id}">${esc(e.title)}</button>`).join('');
      qnav.innerHTML = Array.from({length:60}, (_,i)=>`<button class="qbtn ${i+1===qno?'active':''}" data-q="${i+1}">${i+1}</button>`).join('');
      const paperPages = exam.paperPages || exam.pages;
      paperScroller.innerHTML = paperPages.map(p => `<div class="paper-page-label">第 ${p.page} 页</div><img class="paper" src="${p.image}" alt="原卷第 ${p.page} 页">`).join('');
    }}
    function renderQuestion() {{
      const q = exam.questions.find(x => x.number === qno);
      qTitle.textContent = `第 ${qno} 题`;
      qAnswer.textContent = `答案：${q.answer}`;
      qBody.innerHTML = q.ruby_html || mark(q.body);
      qCn.textContent = q.translation_cn || '（暂无中文翻译）';
      pageLabel.textContent = '可滚动查看整卷';
      const hits = DATA.grammarNotes.filter(n => q.body.includes(n.jp));
      currentGrammar.innerHTML = hits.length
        ? hits.map(n => `<div class="grammar-item"><b>${esc(n.jp)}（${esc(n.kana)}）</b><br>${esc(n.cn)}</div>`).join('')
        : '<div class="hint">当前题暂未匹配到重点语法。阅读题请切换到该组首题查看原文中的语法点。</div>';
      qnav.querySelectorAll('.qbtn').forEach(b => b.classList.toggle('active', Number(b.dataset.q)===qno));
    }}
    function renderOtherViews() {{
      const paperPages = exam.paperPages || exam.pages;
      paperView.innerHTML = paperPages.map(p => `<div class="panel"><div class="head"><h2>原卷第 ${p.page} 页</h2></div><div class="body"><img class="paper" src="${p.image}"></div></div>`).join('');
      answersView.innerHTML = `<div class="panel" style="grid-column:1/-1"><div class="head"><h2>1-60 答案对应表</h2></div><div class="body"><div class="answers">${exam.questions.map(q=>`<div class="answer">${q.number}：${esc(q.answer)}</div>`).join('')}</div></div></div><div class="panel" style="grid-column:1/-1"><div class="head"><h2>答案解析文本</h2></div><div class="body"><div class="jp">${mark(exam.answerText)}</div></div></div>`;
      grammarView.innerHTML = `<div class="panel" style="grid-column:1/-1"><div class="head"><h2>重点语法讲解</h2></div><div class="body">${DATA.grammarNotes.map(n=>`<div class="note"><b>${esc(n.jp)}（${esc(n.kana)}）</b><br>${esc(n.cn)}</div>`).join('')}</div></div>`;
    }}
    function renderAll() {{ renderShell(); renderQuestion(); renderOtherViews(); }}
    document.addEventListener('click', e => {{
      const eb = e.target.closest('[data-exam]'); if (eb) {{ exam = DATA.exams.find(x=>x.id===eb.dataset.exam); qno=1; renderAll(); return; }}
      const qb = e.target.closest('[data-q]'); if (qb) {{ qno=Number(qb.dataset.q); renderQuestion(); return; }}
      const tb = e.target.closest('[data-view]'); if (tb) {{
        document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active', b===tb));
        ['question','paper','answers','grammar'].forEach(v=>document.getElementById(v+'View').classList.toggle('hidden', v!==tb.dataset.view));
      }}
    }});
    navToggle.addEventListener('click', () => {{
      const collapsed = shell.classList.toggle('nav-collapsed');
      navToggle.textContent = collapsed ? '展开题号' : '隐藏题号';
    }});
    renderAll();
  </script>
</body>
</html>""".replace("__DATA__", data).replace("{{", "{").replace("}}", "}")
    (ROOT / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    data = build()
    for exam in data["exams"]:
        print(exam["title"], "questions", len(exam["questions"]), "answers", len(exam["answers"]))
