from concise.core import concise, extract_code, parse_sections


LONG = """# Add retry with exponential backoff

When you are building integrations with third-party APIs, you will eventually
run into rate limits and transient 5xx errors. A naive implementation fails
unpredictably in production, and debugging these failures is painful.

## Why naive retry loops fail

The most common mistake is wrapping the request in a fixed loop.

```python
# DON'T do this: fixed-delay retry amplifies rate limits
while True:
    r = requests.get(url)
    time.sleep(1)
```

Another common mistake is retrying without a cap.

## The implementation

The standard approach is exponential backoff with jitter:

```python
def get_with_retry(url, **kwargs):
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=30)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        if r.status_code not in {429, 502, 503, 504}:
            return r
    raise RuntimeError("gave up")
```

## Verification

Test it with a mock that returns 429 three times and then 200.
"""

SHORT = """# Add retry with exponential backoff

```python
RETRYABLE = {429, 502, 503, 504}

def get_with_retry(url):
    return requests.get(url, timeout=30)
```

検証: モックで確認。
"""


def test_long_input_restructures():
    result = concise(LONG)

    assert "## Conclusion" in result
    assert "## Minimal code" in result
    assert "## How to verify" in result
    assert result.index("get_with_retry") < result.index("DON'T")
    assert "exponential backoff" in result
    assert "429" in result


def test_long_input_shrinks():
    result = concise(LONG)

    assert len(result.splitlines()) < len(LONG.splitlines())


def test_verify_prefers_heading_section():
    result = concise(LONG)

    assert "Test it with a mock" in result


def test_short_input_returned_nearly_unchanged():
    assert concise(SHORT).strip() == SHORT.strip()


def test_japanese_stays_japanese():
    japanese = LONG.replace("Add retry with exponential backoff", "指数バックオフでリトライ追加")
    japanese = japanese.replace(
        "When you are building integrations with third-party APIs, you will eventually\n"
        "run into rate limits and transient 5xx errors. A naive implementation fails\n"
        "unpredictably in production, and debugging these failures is painful.",
        "サードパーティAPIとの統合ではレート制限に遭遇する。単発実装は本番で\n"
        "予測不能に失敗し、事後のデバッグが痛い。要するに指数バックオフが必要だ。",
    )
    japanese = japanese.replace("The most common mistake is wrapping the request in a fixed loop.", "最も多い失敗は固定ループ。")
    japanese = japanese.replace("Another common mistake is retrying without a cap.", "上限なしのリトライも失敗。")
    japanese = japanese.replace("The standard approach is exponential backoff with jitter:", "標準は指数バックオフ+ジッター:")
    japanese = japanese.replace("Test it with a mock that returns 429 three times and then 200.", "429を3回返すモックで確認する。")

    result = concise(japanese)

    assert "## 結論" in result
    assert "要するに" in result
    assert "指数バックオフ" in result
    assert "モックで確認" in result


def test_no_code_blocks():
    text = "## 概要\n\nThis is a long explanation of a concept without any code.\n" * 6

    result = concise(text)

    assert "## Minimal code" not in result
    assert "## Conclusion" in result
    assert "## How to verify" in result


def test_empty_file():
    assert concise("") == "(入力が空です)"
    assert concise("   \n  ") == "(入力が空です)"


def test_extract_code_trims_long_blocks():
    lines = [f"line_{index} = {index}" for index in range(30)]
    sections = [parse_sections("```python\n" + "\n".join(lines) + "\n```")[0]]

    blocks = extract_code(sections)

    assert len(blocks[0].splitlines()) == 26
    assert "省略" in blocks[0]


def test_parse_sections_merges_wrapped_paragraphs():
    sections = parse_sections("# t\n\nfirst part of a sentence\nthat wraps here\n\n## next\n")

    assert sections[0].paras == ["first part of a sentence that wraps here"]
