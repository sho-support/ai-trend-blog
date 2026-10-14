import subprocess
import sys
import time

# 一時的なAPI障害だけを自動再試行するための判定語
TRANSIENT_MARKERS = (
    "503",
    "UNAVAILABLE",
    "high demand",
    "temporarily unavailable",
    "429",
    "RESOURCE_EXHAUSTED",
    "500",
    "502",
    "504",
    "connection reset",
    "connection aborted",
    "read timed out",
    "timeout",
)

# 初回 + 4回再試行
# 合計待機時間: 0 + 30 + 90 + 180 + 300 = 600秒
WAITS = [0, 30, 90, 180, 300]


def is_transient_error(text: str) -> bool:
    lower = text.lower()
    return any(marker.lower() in lower for marker in TRANSIENT_MARKERS)


def main():
    for attempt, wait_seconds in enumerate(WAITS, start=1):
        if wait_seconds:
            print(f"[retry-wrapper] {wait_seconds}秒待ってから再試行します...")
            time.sleep(wait_seconds)

        print(f"[retry-wrapper] generate_article.py 実行 {attempt}/{len(WAITS)}")

        result = subprocess.run(
            [sys.executable, "generate_article.py"],
            text=True,
            capture_output=True,
        )

        if result.stdout:
            print(result.stdout, end="")

        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        if result.returncode == 0:
            print("[retry-wrapper] 記事生成に成功しました。")
            return 0

        combined = f"{result.stdout}\n{result.stderr}"

        if not is_transient_error(combined):
            print(
                "[retry-wrapper] 一時的なAPI障害ではないエラーのため、"
                "自動再試行を中止します。",
                file=sys.stderr,
            )
            return result.returncode

        if attempt < len(WAITS):
            print("[retry-wrapper] 一時的なAPI障害と判定。自動再試行します。")

    print(
        "[retry-wrapper] 一時的なAPI障害が継続し、全再試行に失敗しました。",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
