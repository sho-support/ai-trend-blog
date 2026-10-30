"""Fail fast on Gemini API monthly spending caps, without retrying models.

Monthly caps apply at project/billing-account scope. Falling back to another
model on the same project cannot resolve a billing cap.
"""

def stop_if_monthly_cap_exceeded(error):
    message = str(error).lower()
    if (
        "monthly spending cap" in message
        or "monthly spend cap" in message
    ):
        print(
            "::error title=Gemini API 月間利用上限::"
            "Google AI Studioのプロジェクトまたは請求アカウントの"
            "月間利用上限に達しました。モデル切替・再試行は行いません。"
            "https://aistudio.google.com/spend",
            flush=True,
        )
        raise SystemExit(1)
