const fs = require('fs');
const path = require('path');

const root = __dirname;

function readText(file) {
  return fs.existsSync(file) ? fs.readFileSync(file, 'utf8').trim() : '';
}

function sortedFiles(dir, ext) {
  return fs.readdirSync(dir)
    .filter((name) => name.endsWith(ext))
    .sort((a, b) => {
      const na = Number((a.match(/page-(\d+)/) || [])[1] || 0);
      const nb = Number((b.match(/page-(\d+)/) || [])[1] || 0);
      return na - nb || a.localeCompare(b);
    })
    .map((name) => path.join(dir, name));
}

function pagesFrom(dir, imgDirName) {
  const txtFiles = sortedFiles(dir, '.txt');
  return txtFiles.map((txtFile, index) => {
    const base = path.basename(txtFile, '.txt');
    return {
      page: index + 1,
      image: `${imgDirName}/${base}.png`,
      text: readText(txtFile),
    };
  });
}

function answersFromText(text) {
  const pairs = [];
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length - 1; i += 1) {
    if (!/题号/.test(lines[i]) || !/答案/.test(lines[i + 1])) continue;
    const nums = lines[i].match(/\d+/g) || [];
    const answerLine = lines[i + 1]
      .replace(/答案/g, '')
      .replace(/评分标准.*/, '')
      .trim();
    const vals = answerLine.match(/[A-D]|[ぁ-んァ-ン一-龥ー]+/g) || [];
    nums.forEach((num, idx) => {
      if (vals[idx]) pairs.push({ num, ans: vals[idx] });
    });
  }
  return pairs;
}

const grammarNotes = [
  { jp: 'ため', kana: 'ため', cn: '表示原因或目的；选择题里要结合前后项判断是“为了”还是“因为”。' },
  { jp: 'ように', kana: 'ように', cn: '表示目的、样态或比喻；接动词基本形/ない形时常作“为了能……”。' },
  { jp: 'によって', kana: 'によって', cn: '表示依据、手段、原因或因对象不同而变化。' },
  { jp: 'にとって', kana: 'にとって', cn: '表示“对……来说”，后面多接评价或判断。' },
  { jp: 'として', kana: 'として', cn: '表示身份、资格、立场或功能。' },
  { jp: 'だけでなく', kana: 'だけでなく', cn: '“不仅……而且……”，后项常有「も」。' },
  { jp: 'わけではない', kana: 'わけではない', cn: '部分否定，“并不是……”。' },
  { jp: 'かもしれない', kana: 'かもしれない', cn: '表示可能性，“也许/可能”。' },
  { jp: 'ことがある', kana: 'ことがある', cn: '表示有时会发生某事；注意和经验句「たことがある」区分。' },
  { jp: 'てしまう', kana: 'てしまう', cn: '表示完成、遗憾或不由自主的结果。' },
  { jp: 'てくれる', kana: 'てくれる', cn: '表示别人为我方做某事，或事物给说话人带来积极影响。' },
  { jp: 'ている', kana: 'ている', cn: '表示正在进行、结果状态、反复习惯等。' },
  { jp: 'からこそ', kana: 'からこそ', cn: '强调原因，“正因为……才……”。' },
  { jp: '一方で', kana: 'いっぽうで', cn: '表示转折或并列对比，“另一方面”。' },
  { jp: 'とともに', kana: 'とともに', cn: '表示“和……一起”或“随着……”。' },
  { jp: 'ば', kana: 'ば', cn: '条件形，表示“如果……”。' },
  { jp: 'ても', kana: 'ても', cn: '逆接条件，“即使……也……”。' },
  { jp: 'ながら', kana: 'ながら', cn: '表示同时进行，或逆接“虽然……但是……”。' },
  { jp: 'べき', kana: 'べき', cn: '表示义务、理应，“应该……”。' },
  { jp: 'ものだ', kana: 'ものだ', cn: '表示感叹、常理或回忆。' },
  { jp: 'はず', kana: 'はず', cn: '基于根据的推测，“按理应该……”。' },
];

const furigana = [
  ['静電気', 'せいでんき'], ['乾燥', 'かんそう'], ['衝突', 'しょうとつ'], ['雰囲気', 'ふんいき'],
  ['想像力', 'そうぞうりょく'], ['公共空間', 'こうきょうくうかん'], ['善意', 'ぜんい'],
  ['香り', 'かおり'], ['嗅覚', 'きゅうかく'], ['大脳辺縁系', 'だいのうへんえんけい'],
  ['自律神経', 'じりつしんけい'], ['記憶', 'きおく'], ['言葉', 'ことば'], ['距離', 'きょり'],
  ['理解', 'りかい'], ['感謝', 'かんしゃ'], ['励まし', 'はげまし'], ['責任', 'せきにん'],
  ['馬', 'うま'], ['冷静', 'れいせい'], ['戦争', 'せんそう'], ['徴兵', 'ちょうへい'],
  ['現金', 'げんきん'], ['支払い', 'しはらい'], ['便利', 'べんり'], ['習慣', 'しゅうかん'],
  ['星空', 'ほしぞら'], ['節電', 'せつでん'], ['自然', 'しぜん'], ['未来世代', 'みらいせだい'],
  ['個性', 'こせい'], ['内面', 'ないめん'], ['比較', 'ひかく'], ['卒業生', 'そつぎょうせい'],
];

const exams = [
  {
    id: 'guangdong',
    title: '广东省全国统一考试预测卷',
    subtitle: '2026年高三日语 | 试题 + 答案解析 + 原文',
    source: '2026年广东省全国统一考试预测卷高三日语【试题】.pdf / 【答案解析+原文】.pdf',
    pages: pagesFrom(path.join(root, 'ocr_pages'), 'ocr_pages'),
    answerPages: pagesFrom(path.join(root, 'answer_ocr_pages'), 'answer_ocr_pages'),
    answerSummary: [],
  },
  {
    id: 'henan',
    title: '金太阳·河南2026届高三5月联考',
    subtitle: '高三日语 | 试题 + 参考答案',
    source: '金太阳·河南2026届高三5月联考日语【试题】.pdf / 【参考答案】.pdf',
    pages: pagesFrom(path.join(root, 'henan_ocr_pages'), 'henan_ocr_pages'),
    answerPages: [{ page: 1, image: '', text: readText(path.join(root, 'henan_answers_extracted.txt')) }],
    answerSummary: answersFromText(readText(path.join(root, 'henan_answers_extracted.txt'))),
  },
];

const payload = JSON.stringify({ exams, grammarNotes, furigana });

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>日语试卷解析网页</title>
  <link rel="stylesheet" href="web_assets/base-style.css">
  <style>
    body { background: #f6f8fb; }
    .navbar { height: 56px; }
    .nav-brand { color: #4338ca; }
    .exam-shell { display: grid; grid-template-columns: 240px minmax(0, 1fr); height: calc(100vh - 56px); overflow: hidden; }
    .exam-sidebar { background: #151335; color: #e0e7ff; padding: 14px 12px; overflow-y: auto; }
    .exam-switch { display: grid; gap: 8px; margin-bottom: 14px; }
    .exam-tab { width: 100%; text-align: left; border: 1px solid #37306b; background: #1e1b4b; color: #c7d2fe; border-radius: 8px; padding: 10px; cursor: pointer; }
    .exam-tab.active { background: #4f46e5; color: white; border-color: #818cf8; }
    .side-label { font-size: 12px; color: #a5b4fc; font-weight: 700; margin: 14px 4px 8px; }
    .page-nav { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
    .page-btn { height: 32px; border: 0; border-radius: 8px; background: #2a275e; color: #c7d2fe; font-weight: 700; cursor: pointer; }
    .page-btn:hover, .page-btn.active { background: #10b981; color: white; }
    .exam-main { min-width: 0; overflow-y: auto; }
    .hero-band { background: white; border-bottom: 1px solid #e5e7eb; padding: 16px 20px; display: flex; justify-content: space-between; gap: 12px; align-items: center; }
    .hero-band h1 { font-size: 22px; margin: 0; color: #111827; }
    .hero-band p { margin: 4px 0 0; color: #6b7280; font-size: 13px; }
    .view-tabs { display: flex; flex-wrap: wrap; gap: 8px; }
    .view-tab { border: 1px solid #c7d2fe; background: #eef2ff; color: #3730a3; border-radius: 8px; padding: 7px 12px; cursor: pointer; font-weight: 700; }
    .view-tab.active { background: #4f46e5; color: white; }
    .content-grid { display: grid; grid-template-columns: minmax(360px, 0.94fr) minmax(420px, 1.06fr); gap: 14px; padding: 14px; align-items: start; }
    .panel { background: white; border: 1px solid #e5e7eb; border-radius: 10px; box-shadow: var(--shadow); overflow: hidden; }
    .panel-head { padding: 12px 14px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; gap: 10px; align-items: center; }
    .panel-head h2 { margin: 0; font-size: 15px; color: #374151; }
    .panel-body { padding: 14px; }
    .paper-image { width: 100%; display: block; border-radius: 8px; border: 1px solid #e5e7eb; background: #fff; }
    .ocr-text { white-space: pre-wrap; font-family: var(--font-jp); font-size: 15px; line-height: 1.85; color: #1f2937; }
    ruby rt { color: #4f46e5; font-size: 0.66em; font-weight: 700; }
    .grammar-hit { background: #fff7ed; color: #9a3412; border-bottom: 2px solid #fb923c; border-radius: 4px; padding: 0 2px; font-weight: 700; }
    .note-list { display: grid; gap: 10px; }
    .note { border-left: 4px solid #4f46e5; background: #eef2ff; padding: 10px 12px; border-radius: 8px; }
    .note strong { color: #3730a3; }
    .answer-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(64px, 1fr)); gap: 8px; }
    .answer-pill { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; border-radius: 8px; padding: 7px 8px; text-align: center; font-weight: 700; }
    .hint { font-size: 12px; color: #64748b; }
    .warn { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; }
    .hidden { display: none !important; }
    @media (max-width: 900px) {
      .exam-shell { grid-template-columns: 1fr; height: auto; overflow: visible; }
      .exam-sidebar { position: static; }
      .content-grid { grid-template-columns: 1fr; }
      .hero-band { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <nav class="navbar">
    <div class="nav-brand">高考日语双卷解析</div>
    <div class="nav-center" id="nav-title"></div>
    <div class="nav-links"><span class="nav-link active">本地静态网页</span></div>
  </nav>
  <div class="exam-shell">
    <aside class="exam-sidebar">
      <div class="side-label">试卷切换</div>
      <div class="exam-switch" id="exam-switch"></div>
      <div class="side-label">页码导航</div>
      <div class="page-nav" id="page-nav"></div>
    </aside>
    <main class="exam-main">
      <section class="hero-band">
        <div>
          <h1 id="exam-title"></h1>
          <p id="exam-subtitle"></p>
          <p id="exam-source"></p>
        </div>
        <div class="view-tabs">
          <button class="view-tab active" data-view="paper">原卷对照</button>
          <button class="view-tab" data-view="text">题目文本</button>
          <button class="view-tab" data-view="answers">答案解析</button>
          <button class="view-tab" data-view="grammar">语法重点</button>
        </div>
      </section>
      <section class="content-grid" id="paper-view">
        <div class="panel">
          <div class="panel-head"><h2>原卷页面</h2><span class="hint" id="page-label"></span></div>
          <div class="panel-body"><img class="paper-image" id="paper-image" alt="试卷页面"></div>
        </div>
        <div class="panel">
          <div class="panel-head"><h2>OCR 文本 + 假名标音 + 语法高亮</h2><span class="hint">请以左侧原图复核 OCR</span></div>
          <div class="panel-body"><div class="warn">扫描版 PDF 通过 OCR 生成文本，个别字词可能需要人工校对。日语重点词已添加 ruby 假名，常见语法已高亮。</div><div class="ocr-text" id="page-text"></div></div>
        </div>
      </section>
      <section class="content-grid hidden" id="text-view"></section>
      <section class="content-grid hidden" id="answers-view"></section>
      <section class="content-grid hidden" id="grammar-view"></section>
    </main>
  </div>
  <script>
    const DATA = ${payload};
    let currentExam = DATA.exams[0];
    let currentPage = 1;

    function esc(str) {
      return String(str || '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    }
    function markText(text) {
      let out = esc(text);
      DATA.furigana.forEach(([word, kana]) => {
        out = out.replaceAll(esc(word), '<ruby>' + esc(word) + '<rt>' + esc(kana) + '</rt></ruby>');
      });
      DATA.grammarNotes.forEach((note) => {
        out = out.replaceAll(esc(note.jp), '<span class="grammar-hit" title="' + esc(note.cn) + '">' + esc(note.jp) + '</span>');
      });
      return out;
    }
    function renderExamSwitch() {
      document.getElementById('exam-switch').innerHTML = DATA.exams.map((exam) =>
        '<button class="exam-tab ' + (exam.id === currentExam.id ? 'active' : '') + '" data-exam="' + exam.id + '">' +
        '<strong>' + esc(exam.title) + '</strong><br><span>' + esc(exam.subtitle) + '</span></button>'
      ).join('');
    }
    function renderPageNav() {
      document.getElementById('page-nav').innerHTML = currentExam.pages.map((p) =>
        '<button class="page-btn ' + (p.page === currentPage ? 'active' : '') + '" data-page="' + p.page + '">' + p.page + '</button>'
      ).join('');
    }
    function renderHeader() {
      document.getElementById('nav-title').textContent = currentExam.title;
      document.getElementById('exam-title').textContent = currentExam.title;
      document.getElementById('exam-subtitle').textContent = currentExam.subtitle;
      document.getElementById('exam-source').textContent = '来源：' + currentExam.source;
    }
    function renderPaper() {
      const page = currentExam.pages.find((p) => p.page === currentPage) || currentExam.pages[0];
      document.getElementById('paper-image').src = page.image;
      document.getElementById('page-label').textContent = '第 ' + page.page + ' 页 / 共 ' + currentExam.pages.length + ' 页';
      document.getElementById('page-text').innerHTML = markText(page.text);
    }
    function renderTextView() {
      document.getElementById('text-view').innerHTML = '<div class="panel" style="grid-column:1/-1"><div class="panel-head"><h2>全卷 OCR 文本</h2><span class="hint">已做假名标音和语法高亮</span></div><div class="panel-body"><div class="ocr-text">' +
        currentExam.pages.map((p) => '\\n【第 ' + p.page + ' 页】\\n' + markText(p.text)).join('\\n') + '</div></div></div>';
    }
    function renderAnswersView() {
      const summary = currentExam.answerSummary.length ? '<div class="panel"><div class="panel-head"><h2>客观题答案速览</h2></div><div class="panel-body"><div class="answer-grid">' +
        currentExam.answerSummary.map((x) => '<div class="answer-pill">' + x.num + '：' + esc(x.ans) + '</div>').join('') + '</div></div></div>' : '';
      const detail = '<div class="panel" style="' + (summary ? '' : 'grid-column:1/-1') + '"><div class="panel-head"><h2>答案解析 / 评分标准</h2><span class="hint">来自匹配答案文件</span></div><div class="panel-body"><div class="ocr-text">' +
        currentExam.answerPages.map((p) => '\\n【第 ' + p.page + ' 页】\\n' + markText(p.text)).join('\\n') + '</div></div></div>';
      document.getElementById('answers-view').innerHTML = summary + detail;
    }
    function renderGrammarView() {
      document.getElementById('grammar-view').innerHTML = '<div class="panel" style="grid-column:1/-1"><div class="panel-head"><h2>重点语法讲解</h2><span class="hint">高频句型会在题目文本中橙色高亮</span></div><div class="panel-body"><div class="note-list">' +
        DATA.grammarNotes.map((n) => '<div class="note"><strong>' + esc(n.jp) + '（' + esc(n.kana) + '）</strong><br>' + esc(n.cn) + '</div>').join('') +
        '</div></div></div>';
    }
    function renderAll() {
      renderExamSwitch(); renderPageNav(); renderHeader(); renderPaper(); renderTextView(); renderAnswersView(); renderGrammarView();
    }
    document.addEventListener('click', (e) => {
      const examBtn = e.target.closest('[data-exam]');
      if (examBtn) { currentExam = DATA.exams.find((x) => x.id === examBtn.dataset.exam); currentPage = 1; renderAll(); return; }
      const pageBtn = e.target.closest('[data-page]');
      if (pageBtn) { currentPage = Number(pageBtn.dataset.page); renderPageNav(); renderPaper(); return; }
      const viewBtn = e.target.closest('[data-view]');
      if (viewBtn) {
        document.querySelectorAll('.view-tab').forEach((b) => b.classList.toggle('active', b === viewBtn));
        ['paper','text','answers','grammar'].forEach((v) => document.getElementById(v + '-view').classList.toggle('hidden', v !== viewBtn.dataset.view));
      }
    });
    renderAll();
  </script>
</body>
</html>`;

fs.writeFileSync(path.join(root, 'index.html'), html);
console.log(path.join(root, 'index.html'));
