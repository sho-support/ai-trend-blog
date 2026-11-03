"""Fail fast on Gemini billing blocks, without retrying models.

Monthly caps apply at project/billing-account scope. Falling back to another
model on the same project cannot resolve a billing cap.
"""


def billing_block_reason(error):
    message = str(error).lower()
    if (
        "monthly spending cap" in message
        or "monthly spend cap" in message
    ):
        return (
            "Gemini API 月間利用上限",
            "Google AI Studioのプロジェクトまたは請求アカウントの"
            "月間利用上限に達しました。"
            "https://aistudio.google.com/spend",
        )
    if "prepayment credits are depleted" in message:
        return (
            "Gemini API 前払い残高切れ",
            "Gemini APIの前払い残高がなくなっています。"
            "残高を復旧するまでAI生成を停止してください。"
            "https://ai.studio/projects",
        )
    return None


def stop_if_monthly_cap_exceeded(error):
    """Keep the existing callers, and stop for both caps and prepaid depletion."""
    reason = billing_block_reason(error)
    if reason:
        title, detail = reason
        print(
            f"::error title={title}::[gemini-billing-blocked] {detail} "
            "モデル切替・再試行は行いません。",
            flush=True,
        )
        raise SystemExit(1)
