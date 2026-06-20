from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.models.subscriptions import (
    SubscriptionCheckoutModel,
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


@router.post('/checkout/{plan_id}', response_model=SubscriptionCheckoutModel)
async def create_subscription_checkout(plan_id: str, user=Depends(get_verified_user)):
    plan = await Subscriptions.get_plan_by_id(plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subscription plan not found')
    if plan.price <= 0:
        subscription = await Subscriptions.set_user_subscription(
            UserSubscriptionForm(
                user_id=user.id,
                plan_id=plan_id,
                metadata={'source': 'free_checkout'},
            )
        )
        return SubscriptionCheckoutModel(
            id=subscription.id,
            user_id=user.id,
            plan_id=plan.id,
            status='paid',
            amount=0,
            currency=plan.currency,
            interval=plan.interval,
            metadata={'subscription_id': subscription.id},
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
            completed_at=subscription.created_at,
            plan=plan,
        )
    return await Subscriptions.create_checkout(user.id, plan)


@router.get('/checkout/{checkout_id}', response_model=SubscriptionCheckoutModel)
async def get_subscription_checkout(checkout_id: str, user=Depends(get_verified_user)):
    checkout = await Subscriptions.get_checkout(
        checkout_id,
        user_id=None if user.role == 'admin' else user.id,
    )
    if not checkout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subscription checkout not found')
    return checkout


@router.get('/checkouts', response_model=list[SubscriptionCheckoutModel])
async def get_subscription_checkouts(status_filter: str | None = None, user=Depends(get_admin_user)):
    return await Subscriptions.get_checkouts(status_filter)


@router.post('/checkouts/{checkout_id}/confirm', response_model=SubscriptionCheckoutModel)
async def confirm_subscription_checkout(checkout_id: str, user=Depends(get_admin_user)):
    try:
        return await Subscriptions.complete_checkout(
            checkout_id,
            metadata={'confirmed_by': user.id},
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subscription checkout not found')


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
    if plan.price > 0 and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail='Paid plans require checkout before activation',
        )
    return await Subscriptions.set_user_subscription(UserSubscriptionForm(user_id=user.id, plan_id=plan_id))
