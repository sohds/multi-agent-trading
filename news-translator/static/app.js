const startButton = document.querySelector("#startButton");
const statusBox = document.querySelector("#status");
const results = document.querySelector("#results");

startButton.addEventListener("click", async () => {
  setLoading(true);
  setStatus("뉴스를 가져오고 어려운 표현을 분석하는 중입니다.", false);
  results.replaceChildren();

  try {
    const response = await fetch("/api/start", { method: "POST" });
    const payload = await parseResponse(response);

    if (!response.ok) {
      throw new Error(payload.detail || "분석에 실패했습니다. 잠시 후 다시 시도해주세요.");
    }

    renderResults(payload);
    const failedCount = (payload.articles || []).filter((item) => item.analysis_error).length;
    const message =
      failedCount > 0
        ? `${payload.count}개 기사 처리 완료, ${failedCount}개 기사 LLM 분석 실패`
        : `${payload.count}개 기사 분석 완료`;
    setStatus(message, failedCount > 0);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    setLoading(false);
  }
});

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return {
    detail: text || `서버가 JSON이 아닌 응답을 반환했습니다. HTTP ${response.status}`,
  };
}

function setLoading(isLoading) {
  startButton.disabled = isLoading;
  startButton.textContent = isLoading ? "분석 중" : "시작하기";
}

function setStatus(message, isError) {
  statusBox.textContent = message;
  statusBox.classList.toggle("error", isError);
}

function renderResults(payload) {
  const fragment = document.createDocumentFragment();

  for (const item of payload.articles || []) {
    const article = item.article;
    if (!article) {
      continue;
    }

    const card = document.createElement("article");
    card.className = "article-card";

    const header = document.createElement("header");
    header.className = "article-header";

    const title = document.createElement("h2");
    title.className = "article-title";
    title.textContent = article.title;

    const meta = document.createElement("div");
    meta.className = "meta";
    appendMeta(meta, article.press);
    appendMeta(meta, article.published_at);
    appendMeta(meta, item.analysis_error ? "LLM 분석 실패" : `어려운 표현 ${item.analysis?.difficult_terms?.length || 0}개`);

    header.append(title, meta);

    const body = document.createElement("div");
    body.className = "article-body";
    renderSegments(body, item.segments || [{ text: article.body }]);

    card.append(header, body);

    if (item.analysis_error) {
      const error = document.createElement("div");
      error.className = "article-error";
      error.textContent = item.analysis_error;
      card.append(error);
    }

    const terms = item.analysis?.difficult_terms || [];
    if (terms.length > 0) {
      card.append(renderTermList(terms));
    }

    fragment.append(card);
  }

  results.append(fragment);
}

function appendMeta(parent, value) {
  if (!value) {
    return;
  }
  const span = document.createElement("span");
  span.textContent = value;
  parent.append(span);
}

function renderSegments(parent, segments) {
  for (const segment of segments) {
    if (!segment.term) {
      parent.append(document.createTextNode(segment.text));
      continue;
    }

    const span = document.createElement("span");
    span.className = `term-highlight ${getDifficultyClass(segment.difficulty_score)}`;
    span.tabIndex = 0;
    span.textContent = segment.text;
    const label = segment.canonical_term || segment.term;
    span.dataset.explanation = `${label}: ${segment.explanation}`;
    span.title = segment.explanation;
    parent.append(span);
  }
}

function getDifficultyClass(score) {
  const value = Number(score);

  if (Number.isNaN(value)) {
    return "difficulty-low";
  }
  if (value >= 0.8) {
    return "difficulty-high";
  }
  if (value >= 0.6) {
    return "difficulty-medium";
  }
  return "difficulty-low";
}

function renderTermList(terms) {
  const list = document.createElement("div");
  list.className = "term-list";

  for (const term of terms) {
    const chip = document.createElement("span");
    chip.className = "term-chip";
    const label = term.canonical_term || term.term;
    chip.textContent =
      label === term.term
        ? `${label} ${term.difficulty_score.toFixed(2)}`
        : `${label} (${term.term}) ${term.difficulty_score.toFixed(2)}`;
    if (term.source) {
      chip.title = `source: ${term.source}`;
    }
    list.append(chip);
  }

  return list;
}
