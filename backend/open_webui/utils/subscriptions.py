import time

from fastapi import HTTPException, status

from open_webui.models.subscriptions import SubscriptionPlanModel, SubscriptionUsage, Subscriptions


def _limit_exceeded(name: str, used, limit) -> bool:
    return limit is not None and float(limit) >= 0 and float(used) >= float(limit)


def _allowed_models(plan: SubscriptionPlanModel) -> list[str]:
    return (plan.rules or {}).get('allowed_model_ids') or []


def user_can_use_model(plan: SubscriptionPlanModel, model_id: str) -> bool:
    allowed = _allowed_models(plan)
    return not allowed or model_id in allowed


async def get_subscription_status(user_id: str):
    now = int(time.time())
    plan, subscription = await Subscriptions.get_user_plan(user_id)
    usage_5h = await SubscriptionUsage.summarize(user_id, now - 5 * 60 * 60)
    usage_week = await SubscriptionUsage.summarize(user_id, now - 7 * 24 * 60 * 60)
    return plan, subscription, usage_5h, usage_week


async def check_subscription_access(user_id: str, model_id: str) -> SubscriptionPlanModel:
    plan, _subscription, usage_5h, usage_week = await get_subscription_status(user_id)
    rules = plan.rules or {}

    if not user_can_use_model(plan, model_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f'Your current subscription does not include model "{model_id}".',
        )

    checks = [
        ('weekly message', usage_week.message_count, rules.get('message_limit_per_week')),
        ('5-hour message', usage_5h.message_count, rules.get('message_limit_per_5h')),
        ('weekly token', usage_week.total_tokens, rules.get('token_limit_per_week')),
        ('5-hour token', usage_5h.total_tokens, rules.get('token_limit_per_5h')),
        ('weekly spend', usage_week.amount, rules.get('amount_limit_per_week')),
        ('5-hour spend', usage_5h.amount, rules.get('amount_limit_per_5h')),
    ]
    for label, used, limit in checks:
        if _limit_exceeded(label, used, limit):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f'Your subscription {label} limit has been reached.',
            )

    return plan


async def record_subscription_usage(user_id: str, plan: SubscriptionPlanModel, model_id: str, usage: dict, metadata: dict):
    if not usage:
        return
    amount = SubscriptionUsage.calculate_amount(plan, model_id, usage)
    await SubscriptionUsage.record(
        user_id=user_id,
        plan_id=plan.id,
        model_id=model_id,
        usage=usage,
        chat_id=metadata.get('chat_id'),
        message_id=metadata.get('message_id') or metadata.get('assistant_message_id'),
        amount=amount,
    )
