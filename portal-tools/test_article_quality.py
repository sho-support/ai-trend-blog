#!/usr/bin/env python3
"""Exercise the real generator function with a stub model; never calls an API."""
import ast
import contextlib
import io
import re
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from article_quality import article_quality_errors

SOURCE = 'https://example.test/official-announcement/'
paragraphs = [
    f'テスト資料の項目{i}です。確認できた機能と対象の条件を整理し、使う前に必要な設定を説明します。'
    f'この項目{i}で扱う手順と公開範囲を記載し、利用者が次に確認する場所を具体的に案内します。'
    f'項目{i}の検証には実際の操作と公式に示された数値の照合が必要です。'
    for i in range(6)
]
VALID = '<h1>テスト用：対象プランと設定手順</h1>' + ''.join(
    ('<h2>対象プランの条件</h2>' if i == 1 else '<h2>設定を確認する手順</h2>' if i == 4 else '') + '<p>' + p + '</p>'
    for i, p in enumerate(paragraphs)
)


def main():
    assert not article_quality_errors(VALID, SOURCE), article_quality_errors(VALID, SOURCE)
    assert article_quality_errors(VALID + '<script>alert(1)</script>', SOURCE)
    assert article_quality_errors(VALID.replace('<p>', '<p onclick="alert(1)">', 1), SOURCE)
    assert article_quality_errors(VALID + '<p>' + paragraphs[0] + '</p>', SOURCE)
    assert article_quality_errors('<h1>短い</h1><h2>見出し</h2><p>内容不足</p>', SOURCE)
    assert article_quality_errors(VALID + '<p><a href="https://attacker.example/">案内</a></p>', SOURCE)
    assert not article_quality_errors(VALID + '<p><a href="'+SOURCE+'">公式の案内</a></p>', SOURCE)
    assert article_quality_errors(VALID + '<p>いかがでしたか。</p>', SOURCE)
    # Compile the actual production function without constructing a real API client.
    tree = ast.parse((ROOT/'generate_article.py').read_text(encoding='utf-8'))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'generate_article')
    namespace = {'re':re, 'article_quality_errors':article_quality_errors}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(ROOT/'generate_article.py'), 'exec'), namespace)
    candidate = {'source_name':'Test', 'title':'テスト記事', 'url':SOURCE}
    calls = []

    def valid_model(prompt, purpose):
        calls.append(prompt)
        return SimpleNamespace(text=VALID)

    namespace['generate_content_with_fallback'] = valid_model
    with contextlib.redirect_stdout(io.StringIO()):
        assert namespace['generate_article'](candidate, 'テスト用の公式本文') == VALID
    assert len(calls) == 1, 'natural, topic-specific headings should not require a rewrite'
    outputs = iter([VALID + '<p>'+paragraphs[0]+'</p>', VALID])
    prompts = []

    def repair_model(prompt, purpose):
        prompts.append(prompt)
        return SimpleNamespace(text=next(outputs))

    namespace['generate_content_with_fallback'] = repair_model
    with contextlib.redirect_stdout(io.StringIO()):
        assert namespace['generate_article'](candidate, 'テスト用の公式本文') == VALID
    assert len(prompts) == 2 and '同じ段落の繰り返し' in prompts[1], 'repair must use the actual failed check'

    def capped_model(prompt, purpose):
        raise SystemExit(1)

    namespace['generate_content_with_fallback'] = capped_model
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            namespace['generate_article'](candidate, 'テスト用の公式本文')
        except SystemExit as error:
            assert error.code == 1
        else:
            raise AssertionError('billing cap was swallowed')
    print('PASS: editorial quality, topic-specific headings, repair and billing-cap propagation (no API calls)')


if __name__ == '__main__':
    main()
