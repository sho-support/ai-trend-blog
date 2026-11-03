"""Offline publication checks for generated editorial HTML.

These checks enforce structure, links and obvious repetition. They do not
claim to verify factual correctness or replace an editorial fact check.
"""
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit


class _Article(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h1 = 0
        self.h2 = 0
        self.parts = []
        self.paragraphs = []
        self.paragraph = None
        self.unsafe = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        allowed = {"h1", "h2", "h3", "p", "strong", "em", "a", "ul", "ol", "li", "table", "caption", "thead", "tbody", "tfoot", "tr", "th", "td"}
        if tag not in allowed:
            self.unsafe = True
        if any(name.lower().startswith("on") or name.lower() in {"style", "srcdoc"} for name, _ in attrs):
            self.unsafe = True
        if tag == "h1": self.h1 += 1
        if tag == "h2": self.h2 += 1
        if tag == "a": self.links.append(dict(attrs).get("href", ""))
        if tag == "p": self.paragraph = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        self.parts.append(data)
        if self.paragraph is not None: self.paragraph.append(data)

    def handle_endtag(self, tag):
        if tag == "p" and self.paragraph is not None:
            self.paragraphs.append("".join(self.paragraph))
            self.paragraph = None


def article_quality_errors(body, source_url):
    article = _Article()
    article.feed(body)
    errors = []
    if article.unsafe: errors.append("実行コード・装飾・フォーム等の不要なHTMLがあります")
    if article.h1 != 1: errors.append("タイトルのh1は1つにしてください")
    if not 1 <= article.h2 <= 3: errors.append("話題に合ったh2を1〜3個に整理してください")
    text = re.sub(r"\s+", "", "".join(article.parts))
    if not 250 <= len(text) <= 1000:
        errors.append("本文は250〜1000文字で、使い道と最初の一歩に絞ってください")
    title = re.search(r'<h1[^>]*>(.*?)</h1>', body, re.S)
    if title and len(re.sub(r'<[^>]+>|\s', '', title.group(1))) > 42:
        errors.append("タイトルは42文字以内で、何ができるかを先に書いてください")
    if any(len(re.sub(r'\s', '', p)) > 160 for p in article.paragraphs):
        errors.append("長い段落を分け、1段落を160文字以内にしてください")
    if re.search(r'(誰でも|必ず|確実に|放置で).{0,8}(稼げ|儲か|収益)', text):
        errors.append("収益を保証する表現を除き、作れるものと必要な作業を示してください")
    if len(article.paragraphs) < 3: errors.append("段落を分けて具体的に説明してください")
    paragraphs = [re.sub(r"\s+", "", p) for p in article.paragraphs if len(p.strip()) >= 40]
    if len(paragraphs) != len(set(paragraphs)): errors.append("同じ段落の繰り返しを除いてください")
    if any(phrase in text for phrase in ("いかがでしたか", "今後の動向に注目していきましょう", "最後までお読みいただき")):
        errors.append("定型の挨拶や内容のない締めを省いてください")
    official = urlsplit(source_url)
    for link in article.links:
        parsed = urlsplit(link)
        if link != source_url or parsed.scheme != "https" or parsed.netloc != official.netloc:
            errors.append("本文の出典リンクは確認済み公式URLだけを使ってください")
            break
    return errors
