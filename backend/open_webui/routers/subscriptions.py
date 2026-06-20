from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.models.subscriptions import (
    SubscriptionPlanForm,
    SubscriptionStatus,
    Subscriptions,
    UserSubscriptionForm,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.subscriptions import get_subscription_status

router = APIRouter()


@router.get('/plans')
async def get_subscription_plans(user=Depends(get_verified_user)):
    return await Subscriptions.get_plans(active_only=user.role != 'admin')


@router.get('/status', response_model=SubscriptionStatus)
async def get_my_subscription_status(user=Depends(get_verified_user)):
    plan, subscription, usage_5h, usage_week = await get_subscription_status(user.id)
    return SubscriptionStatus(plan=plan, subscription=subscription, usage_5h=usage_5h, usage_week=usage_week)


@router.post('/plans/upsert')
async def upsert_subscription_plan(form_data: SubscriptionPlanForm, user=Depends(get_admin_user)):
    return await Subscriptions.upsert_plan(form_data)


@router.post('/users/assign')
async def assign_user_subscription(form_data: UserSubscriptionForm, user=Depends(get_admin_user)):
    if not await Subscriptions.get_plan_by_id(form_data.plan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subscription plan not found')
    return await Subscriptions.set_user_subscription(form_data)


@router.post('/select/{plan_id}')
async def select_subscription_plan(plan_id: str, user=Depends(get_verified_user)):
    plan = await Subscriptions.get_plan_by_id(plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subscription plan not found')
    return await Subscriptions.set_user_subscription(UserSubscriptionForm(user_id=user.id, plan_id=plan_id))
