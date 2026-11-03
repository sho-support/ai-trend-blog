"""Queue one fresh AI-use post without an LLM, thread, or model charge."""
import argparse
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parent
POLICY=json.loads((ROOT/'growth/channel-policy.json').read_text())
BUFFER_API_URL='https://api.buffer.com'
BUFFER_API_KEY=os.environ.get('BUFFER_API_KEY')
SITE_BASE_URL='https://sho-support.github.io/ai-trend-blog'
HISTORY_FILE=ROOT/'article_history.json'
BUFFER_HISTORY_FILE=ROOT/'buffer_post_history.json'
TARGET_X_HANDLE=POLICY['ai']['handle']
TARGET_X_CHANNEL=POLICY['ai']['channel_id']
JST=timezone(timedelta(hours=9))
MAX_X_WEIGHT=270
URL_WEIGHT=23

def buffer_graphql(query):
    request = Request(
        BUFFER_API_URL,
        headers={
            "Authorization":
                f"Bearer {BUFFER_API_KEY}",
            "Content-Type":
                "application/json",
        },
        data=json.dumps({"query":query}).encode(),
        method='POST',
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    if payload.get("errors"):
        raise RuntimeError(
            "Buffer GraphQL error: "
            + str(
                payload["errors"]
            )
        )

    return payload.get(
        "data",
        {},
    )

def load_json_list(path):
    if not path.exists():
        return []

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(
            value,
            list,
        ):
            return value

        return []

    except Exception:
        return []

def x_char_weight(ch):
    code = ord(ch)

    if (
        0x0000 <= code <= 0x10FF
        or 0x2000 <= code <= 0x200D
        or 0x2010 <= code <= 0x201F
        or 0x2032 <= code <= 0x2037
    ):
        return 1

    return 2

def x_weighted_length(text):
    total = 0
    last_end = 0

    for match in re.finditer(
        r"https?://\S+",
        text,
    ):
        plain = text[
            last_end:
            match.start()
        ]

        total += sum(
            x_char_weight(ch)
            for ch in plain
        )

        total += URL_WEIGHT

        last_end = (
            match.end()
        )

    tail = text[
        last_end:
    ]

    total += sum(
        x_char_weight(ch)
        for ch in tail
    )

    return total

def truncate_to_weight(
    text,
    max_weight,
):
    text = text.strip()

    if (
        x_weighted_length(text)
        <= max_weight
    ):
        return text

    result = []
    current_weight = 0

    for ch in text:
        weight = (
            x_char_weight(ch)
        )

        if (
            current_weight
            + weight
            + 2
            > max_weight
        ):
            break

        result.append(ch)

        current_weight += weight

    return (
        "".join(result).rstrip()
        + "…"
    )

def already_queued_today(
    posted,
    today_jst,
):
    for item in posted:
        if (
            item.get(
                "queued_date_jst"
            )
            == today_jst
        ):
            return True

    return False

def get_x_channel_id():
    account=buffer_graphql('query { account { organizations { id } } }')
    for org in account.get('account',{}).get('organizations',[]):
        org_id=org.get('id','')
        if not re.fullmatch(r'[0-9a-fA-F]{24}',org_id):
            continue
        data=buffer_graphql('query { channels(input:{organizationId:'+json.dumps(org_id)+'}) '
                            '{ id service externalLink isDisconnected isLocked } }')
        for channel in data.get('channels',[]):
            if channel.get('id')!=TARGET_X_CHANNEL:
                continue
            link=channel.get('externalLink','').rstrip('/').lower()
            expected={('https://'+host+'/'+TARGET_X_HANDLE).lower() for host in ('twitter.com','x.com','www.twitter.com','www.x.com')}
            if channel.get('service')!='twitter' or channel.get('isDisconnected') or channel.get('isLocked') or link not in expected:
                raise RuntimeError('指定したAI用Xアカウントを利用できません。')
            return TARGET_X_CHANNEL
    raise RuntimeError('指定したAI用Xアカウントが見つかりません。別のアカウントには送信しません。')


def is_fresh(item,now):
    try:
        created=datetime.fromisoformat(item['created_at'].replace('Z','+00:00'))
        return created.tzinfo is not None and timedelta(0)<=now-created<=timedelta(days=3)
    except (KeyError,TypeError,ValueError):
        return False


def create_post_copy(item):
    filename=item.get('filename','')
    if not re.fullmatch(r'[a-zA-Z0-9_-]+\.html',filename):
        raise ValueError('Invalid article filename.')
    article_url=SITE_BASE_URL+'/articles/'+filename
    # Reviewed copy is part of the article, not another paid model request.
    copy=item.get('social_copy') or item.get('title','')
    copy=re.sub(r'https?://\S+','',copy).strip()
    copy=re.sub(r'\n{3,}','\n\n',copy)
    if not copy:
        raise ValueError('投稿する記事の要点がありません。')
    if re.search(r'(誰でも|必ず|確実に|放置で).{0,8}(稼げ|儲か|収益)',copy):
        raise ValueError('収益を保証する投稿文は使えません。')
    copy=truncate_to_weight(copy,MAX_X_WEIGHT-URL_WEIGHT-2)
    return copy+'\n\n'+article_url


def create_buffer_post(channel_id,text):
    data=buffer_graphql('mutation { createPost(input:{text:'+json.dumps(text,ensure_ascii=False)+
                        ',channelId:'+json.dumps(channel_id)+',schedulingType:automatic,mode:addToQueue,aiAssisted:true}) '
                        '{ ... on PostActionSuccess { post { id dueAt status } } ... on MutationError { message } } }')
    result=data.get('createPost',{});message=result.get('message') or ''
    if message:
        lower=message.lower()
        if 'scheduled posts' in lower and 'limit' in lower:
            print('Buffer予約枠が満杯です。今回は追加せず、記事は保存済みです。')
            return None
        raise RuntimeError('Buffer投稿予約失敗: '+message)
    post=result.get('post')
    if not post or not post.get('id'):
        raise RuntimeError('Buffer投稿予約の結果を確認できません。')
    return post


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    now=datetime.now(JST);today=now.date().isoformat()
    history=load_json_list(HISTORY_FILE);posted=load_json_list(BUFFER_HISTORY_FILE)
    sent={x.get('filename') for x in posted}
    pending=[x for x in history if x.get('filename') not in sent and is_fresh(x,now)]
    if not pending:
        print('3日以内の新しいAI記事がないため、古い記事は予約しません。');return
    latest=max(pending,key=lambda x:datetime.fromisoformat(x['created_at'].replace('Z','+00:00')))
    text=create_post_copy(latest)
    if args.dry_run:
        print(json.dumps({'mode':'draft_only','handle':TARGET_X_HANDLE,'text':text,'llm_calls':0},ensure_ascii=False));return
    if now.weekday()>=5 or already_queued_today(posted,today):
        print('土日、または本日予約済みのため、追加しません。');return
    if not BUFFER_API_KEY:
        raise RuntimeError('BUFFER_API_KEY が設定されていません。')
    post=create_buffer_post(get_x_channel_id(),text)
    if post is None:return
    posted.append({'filename':latest['filename'],'buffer_post_id':post['id'],'due_at':post.get('dueAt'),
                   'queued_date_jst':today,'type':'twitter_single_post'})
    BUFFER_HISTORY_FILE.write_text(json.dumps(posted,ensure_ascii=False,indent=2),encoding='utf-8')
    print('AI記事の投稿を1件予約しました:',post)


if __name__=='__main__':main()
