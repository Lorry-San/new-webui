import logging
import hashlib
import time
from typing import Optional
from urllib.parse import urlencode
from uuid import uuid4

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, BigInteger, Boolean, Column, Float, Index, Text, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


DEFAULT_PLAN_ID = 'free'


DEFAULT_PLANS = [
    {
        'id': 'free',
        'name': 'Free',
        'description': 'Explore core models with a small weekly allowance.',
        'price': 0,
        'currency': 'JPY',
        'interval': 'month',
        'features': ['Core models', 'Limited weekly messages', 'Limited token budget'],
        'rules': {
            'plan_rank': 0,
            'allowed_model_ids': [],
            'message_limit_per_week': 50,
            'message_limit_per_5h': 10,
            'token_limit_per_week': 100000,
            'amount_limit_per_week': 0,
            'default_input_token_price_per_1k': 0,
            'default_output_token_price_per_1k': 0,
            'model_prices': {},
        },
        'sort_order': 0,
    },
    {
        'id': 'go',
        'name': 'Go',
        'description': 'More room for everyday chat and uploads.',
        'price': 1400,
        'currency': 'JPY',
        'interval': 'month',
        'features': ['More messages', 'More uploads', 'Higher token budget'],
        'rules': {
            'plan_rank': 10,
            'allowed_model_ids': [],
            'message_limit_per_week': 500,
            'message_limit_per_5h': 80,
            'token_limit_per_week': 1000000,
            'amount_limit_per_week': 1000,
            'amount_limit_per_5h': 200,
            'default_input_token_price_per_1k': 0,
            'default_output_token_price_per_1k': 0,
            'model_prices': {},
        },
        'sort_order': 10,
    },
    {
        'id': 'plus',
        'name': 'Plus',
        'description': 'Higher limits and access to advanced models.',
        'price': 3000,
        'currency': 'JPY',
        'interval': 'month',
        'features': ['Advanced models', 'Higher message limits', 'Larger token budget'],
        'rules': {
            'plan_rank': 20,
            'allowed_model_ids': [],
            'message_limit_per_week': 2000,
            'message_limit_per_5h': 200,
            'token_limit_per_week': 5000000,
            'amount_limit_per_week': 5000,
            'amount_limit_per_5h': 800,
            'default_input_token_price_per_1k': 0,
            'default_output_token_price_per_1k': 0,
            'model_prices': {},
        },
        'sort_order': 20,
    },
    {
        'id': 'pro',
        'name': 'Pro',
        'description': 'Highest limits for heavy professional use.',
        'price': 16800,
        'currency': 'JPY',
        'interval': 'month',
        'features': ['All Plus features', 'Highest usage limits', 'Priority model access'],
        'rules': {
            'plan_rank': 30,
            'allowed_model_ids': [],
            'message_limit_per_week': 10000,
            'message_limit_per_5h': 1000,
            'token_limit_per_week': 25000000,
            'amount_limit_per_week': 25000,
            'amount_limit_per_5h': 4000,
            'default_input_token_price_per_1k': 0,
            'default_output_token_price_per_1k': 0,
            'model_prices': {},
        },
        'sort_order': 30,
    },
]


class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plan'

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False, default=0)
    currency = Column(Text, nullable=False, default='USD')
    interval = Column(Text, nullable=False, default='month')
    features = Column(JSON, nullable=True)
    rules = Column(JSON, nullable=False, default={})
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(BigInteger, nullable=False, default=0)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class UserSubscription(Base):
    __tablename__ = 'user_subscription'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False, index=True)
    plan_id = Column(Text, nullable=False, index=True)
    status = Column(Text, nullable=False, default='active')
    current_period_start = Column(BigInteger, nullable=True)
    current_period_end = Column(BigInteger, nullable=True)
    meta = Column('metadata', JSON, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (Index('ix_user_subscription_user_status', 'user_id', 'status'),)


class SubscriptionUsageEvent(Base):
    __tablename__ = 'subscription_usage_event'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False, index=True)
    plan_id = Column(Text, nullable=False, index=True)
    model_id = Column(Text, nullable=True, index=True)
    chat_id = Column(Text, nullable=True)
    message_id = Column(Text, nullable=True)
    input_tokens = Column(BigInteger, nullable=False, default=0)
    output_tokens = Column(BigInteger, nullable=False, default=0)
    total_tokens = Column(BigInteger, nullable=False, default=0)
    amount = Column(Float, nullable=False, default=0)
    created_at = Column(BigInteger, nullable=False, index=True)


class SubscriptionCheckout(Base):
    __tablename__ = 'subscription_checkout'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False, index=True)
    plan_id = Column(Text, nullable=False, index=True)
    status = Column(Text, nullable=False, default='pending', index=True)
    amount = Column(Float, nullable=False, default=0)
    currency = Column(Text, nullable=False, default='USD')
    interval = Column(Text, nullable=False, default='month')
    checkout_url = Column(Text, nullable=True)
    meta = Column('metadata', JSON, nullable=True)
    created_at = Column(BigInteger, nullable=False, index=True)
    updated_at = Column(BigInteger, nullable=False)
    completed_at = Column(BigInteger, nullable=True)


class SubscriptionPaymentProvider(Base):
    __tablename__ = 'subscription_payment_provider'

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    provider_type = Column(Text, nullable=False, default='manual')
    config = Column(JSON, nullable=False, default={})
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(BigInteger, nullable=False, default=0)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class SubscriptionPlanModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    price: float = 0
    currency: str = 'USD'
    interval: str = 'month'
    features: list[str] = Field(default_factory=list)
    rules: dict = Field(default_factory=dict)
    is_active: bool = True
    sort_order: int = 0
    created_at: int
    updated_at: int


class SubscriptionPlanForm(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: float = 0
    currency: str = 'USD'
    interval: str = 'month'
    features: list[str] = Field(default_factory=list)
    rules: dict = Field(default_factory=dict)
    is_active: bool = True
    sort_order: int = 0


class UserSubscriptionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    user_id: str
    plan_id: str
    status: str = 'active'
    current_period_start: Optional[int] = None
    current_period_end: Optional[int] = None
    metadata: Optional[dict] = Field(default=None, validation_alias='meta')
    created_at: int
    updated_at: int


class UserSubscriptionForm(BaseModel):
    user_id: str
    plan_id: str
    status: str = 'active'
    current_period_start: Optional[int] = None
    current_period_end: Optional[int] = None
    metadata: Optional[dict] = None


class UsageSummary(BaseModel):
    message_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    amount: float = 0


class SubscriptionStatus(BaseModel):
    plan: SubscriptionPlanModel
    subscription: Optional[UserSubscriptionModel] = None
    usage_5h: UsageSummary
    usage_week: UsageSummary


class SubscriptionCheckoutModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    user_id: str
    plan_id: str
    status: str = 'pending'
    amount: float = 0
    currency: str = 'USD'
    interval: str = 'month'
    checkout_url: Optional[str] = None
    metadata: Optional[dict] = Field(default=None, validation_alias='meta')
    created_at: int
    updated_at: int
    completed_at: Optional[int] = None
    plan: Optional[SubscriptionPlanModel] = None


class SubscriptionPaymentProviderModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    provider_type: str = 'manual'
    config: dict = Field(default_factory=dict)
    is_active: bool = True
    sort_order: int = 0
    created_at: int
    updated_at: int


class SubscriptionPaymentProviderForm(BaseModel):
    id: str
    name: str
    provider_type: str = 'manual'
    config: dict = Field(default_factory=dict)
    is_active: bool = True
    sort_order: int = 0


class SubscriptionPaymentProviderPublicModel(BaseModel):
    id: str
    name: str
    provider_type: str = 'manual'
    config: dict = Field(default_factory=dict)


class SubscriptionCheckoutPaymentForm(BaseModel):
    provider_id: str


class SubscriptionUsageTable:
    @staticmethod
    def calculate_amount(plan: SubscriptionPlanModel, model_id: str, usage: dict) -> float:
        rules = plan.rules or {}
        prices = rules.get('model_prices') or {}
        model_price = prices.get(model_id) or prices.get('*') or {}
        input_price = model_price.get('input_token_price_per_1k', rules.get('default_input_token_price_per_1k', 0))
        output_price = model_price.get('output_token_price_per_1k', rules.get('default_output_token_price_per_1k', 0))
        input_tokens = int(usage.get('input_tokens') or usage.get('prompt_tokens') or 0)
        output_tokens = int(usage.get('output_tokens') or usage.get('completion_tokens') or 0)
        return round(
            (input_tokens / 1000 * float(input_price or 0)) + (output_tokens / 1000 * float(output_price or 0)), 6
        )

    async def record(
        self,
        user_id: str,
        plan_id: str,
        model_id: str,
        usage: dict,
        chat_id: Optional[str] = None,
        message_id: Optional[str] = None,
        amount: float = 0,
        db: Optional[AsyncSession] = None,
    ) -> None:
        input_tokens = int(usage.get('input_tokens') or usage.get('prompt_tokens') or 0)
        output_tokens = int(usage.get('output_tokens') or usage.get('completion_tokens') or 0)
        async with get_async_db_context(db) as db:
            db.add(
                SubscriptionUsageEvent(
                    id=str(uuid4()),
                    user_id=user_id,
                    plan_id=plan_id,
                    model_id=model_id,
                    chat_id=chat_id,
                    message_id=message_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=int(usage.get('total_tokens') or input_tokens + output_tokens),
                    amount=amount,
                    created_at=int(time.time()),
                )
            )
            await db.commit()

    async def summarize(self, user_id: str, since: int, db: Optional[AsyncSession] = None) -> UsageSummary:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(
                    func.count(SubscriptionUsageEvent.id),
                    func.coalesce(func.sum(SubscriptionUsageEvent.input_tokens), 0),
                    func.coalesce(func.sum(SubscriptionUsageEvent.output_tokens), 0),
                    func.coalesce(func.sum(SubscriptionUsageEvent.total_tokens), 0),
                    func.coalesce(func.sum(SubscriptionUsageEvent.amount), 0),
                )
                .where(SubscriptionUsageEvent.user_id == user_id)
                .where(SubscriptionUsageEvent.created_at >= since)
            )
            row = result.one()
            return UsageSummary(
                message_count=row[0] or 0,
                input_tokens=row[1] or 0,
                output_tokens=row[2] or 0,
                total_tokens=row[3] or 0,
                amount=float(row[4] or 0),
            )


class SubscriptionsTable:
    @staticmethod
    def get_plan_rank(plan: Optional[SubscriptionPlanModel]) -> int:
        if not plan:
            return 0
        rules = plan.rules or {}
        return int(rules.get('plan_rank', plan.sort_order or 0) or 0)

    async def assert_plan_change_allowed(
        self,
        user_id: str,
        target_plan: SubscriptionPlanModel,
        db: Optional[AsyncSession] = None,
    ) -> None:
        current_plan, subscription = await self.get_user_plan(user_id, db=db)
        now = int(time.time())
        if (
            subscription
            and subscription.current_period_end
            and subscription.current_period_end > now
            and self.get_plan_rank(current_plan) > self.get_plan_rank(target_plan)
        ):
            raise ValueError('Cannot downgrade during the current subscription period')

    async def ensure_default_plans(self, db: Optional[AsyncSession] = None) -> None:
        async with get_async_db_context(db) as db:
            count = (await db.execute(select(func.count()).select_from(SubscriptionPlan))).scalar() or 0
            if count > 0:
                return
            now = int(time.time())
            for plan in DEFAULT_PLANS:
                db.add(SubscriptionPlan(**plan, is_active=True, created_at=now, updated_at=now))
            await db.commit()

    async def get_plans(
        self, active_only: bool = True, db: Optional[AsyncSession] = None
    ) -> list[SubscriptionPlanModel]:
        async with get_async_db_context(db) as db:
            await self.ensure_default_plans(db)
            stmt = select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order.asc(), SubscriptionPlan.price.asc())
            if active_only:
                stmt = stmt.where(SubscriptionPlan.is_active == True)
            rows = (await db.execute(stmt)).scalars().all()
            return [SubscriptionPlanModel.model_validate(row) for row in rows]

    async def get_plan_by_id(self, plan_id: str, db: Optional[AsyncSession] = None) -> Optional[SubscriptionPlanModel]:
        async with get_async_db_context(db) as db:
            await self.ensure_default_plans(db)
            row = await db.get(SubscriptionPlan, plan_id)
            return SubscriptionPlanModel.model_validate(row) if row else None

    async def create_checkout(
        self, user_id: str, plan: SubscriptionPlanModel, db: Optional[AsyncSession] = None
    ) -> SubscriptionCheckoutModel:
        async with get_async_db_context(db) as db:
            await self.assert_plan_change_allowed(user_id, plan, db=db)
            now = int(time.time())
            checkout_id = str(uuid4())
            payment_url = (plan.rules or {}).get('payment_url') or ''
            checkout_url = payment_url.format(order_id=checkout_id, plan_id=plan.id) if payment_url else None
            row = SubscriptionCheckout(
                id=checkout_id,
                user_id=user_id,
                plan_id=plan.id,
                amount=plan.price,
                currency=plan.currency,
                interval=plan.interval,
                checkout_url=checkout_url,
                status='pending',
                meta={'plan_name': plan.name},
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            model = SubscriptionCheckoutModel.model_validate(row)
            model.plan = plan
            return model

    def sanitize_payment_provider(
        self, provider: SubscriptionPaymentProviderModel
    ) -> SubscriptionPaymentProviderPublicModel:
        config = {
            key: value
            for key, value in (provider.config or {}).items()
            if key not in {'key', 'secret', 'private_key', 'api_key'}
        }
        return SubscriptionPaymentProviderPublicModel(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type,
            config=config,
        )

    async def get_payment_providers(
        self, active_only: bool = True, db: Optional[AsyncSession] = None
    ) -> list[SubscriptionPaymentProviderModel]:
        async with get_async_db_context(db) as db:
            stmt = select(SubscriptionPaymentProvider).order_by(
                SubscriptionPaymentProvider.sort_order.asc(), SubscriptionPaymentProvider.created_at.asc()
            )
            if active_only:
                stmt = stmt.where(SubscriptionPaymentProvider.is_active == True)
            rows = (await db.execute(stmt)).scalars().all()
            return [SubscriptionPaymentProviderModel.model_validate(row) for row in rows]

    async def get_payment_provider_by_id(
        self, provider_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[SubscriptionPaymentProviderModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(SubscriptionPaymentProvider, provider_id)
            return SubscriptionPaymentProviderModel.model_validate(row) if row else None

    async def upsert_payment_provider(
        self, form: SubscriptionPaymentProviderForm, db: Optional[AsyncSession] = None
    ) -> SubscriptionPaymentProviderModel:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            row = await db.get(SubscriptionPaymentProvider, form.id)
            if row:
                for key, value in form.model_dump().items():
                    setattr(row, key, value)
                row.updated_at = now
            else:
                row = SubscriptionPaymentProvider(**form.model_dump(), created_at=now, updated_at=now)
                db.add(row)
            await db.commit()
            await db.refresh(row)
            return SubscriptionPaymentProviderModel.model_validate(row)

    @staticmethod
    def build_epay_sign(params: dict, key: str) -> str:
        raw = '&'.join(
            f'{name}={params[name]}'
            for name in sorted(params)
            if name not in {'sign', 'sign_type'} and params[name] not in (None, '')
        )
        return hashlib.md5(f'{raw}{key}'.encode()).hexdigest()

    async def create_checkout_payment(
        self,
        checkout_id: str,
        provider_id: str,
        base_url: str,
        db: Optional[AsyncSession] = None,
    ) -> SubscriptionCheckoutModel:
        async with get_async_db_context(db) as db:
            row = await db.get(SubscriptionCheckout, checkout_id)
            if not row:
                raise ValueError('Subscription checkout not found')
            if row.status != 'pending':
                model = SubscriptionCheckoutModel.model_validate(row)
                model.plan = await self.get_plan_by_id(row.plan_id, db=db)
                return model

            provider = await self.get_payment_provider_by_id(provider_id, db=db)
            if not provider or not provider.is_active:
                raise ValueError('Payment provider not found')

            plan = await self.get_plan_by_id(row.plan_id, db=db)
            now = int(time.time())
            checkout_url = None
            metadata = row.meta or {}
            if provider.provider_type == 'epay':
                config = provider.config or {}
                api_url = str(config.get('api_url') or '').rstrip('/')
                pid = str(config.get('pid') or '')
                key = str(config.get('key') or '')
                pay_type = str(config.get('pay_type') or 'alipay')
                if not api_url or not pid or not key:
                    raise ValueError('ePay provider is not configured')
                params = {
                    'pid': pid,
                    'type': pay_type,
                    'out_trade_no': row.id,
                    'notify_url': f'{base_url.rstrip("/")}/api/v1/subscriptions/payments/epay/notify/{provider.id}',
                    'return_url': f'{base_url.rstrip("/")}/orders/{row.id}',
                    'name': plan.name if plan else row.plan_id,
                    'money': f'{float(row.amount):.2f}',
                    'sitename': config.get('sitename') or 'new-webui',
                }
                params['sign'] = self.build_epay_sign(params, key)
                params['sign_type'] = 'MD5'
                checkout_url = f'{api_url}/submit.php?{urlencode(params)}'
            else:
                checkout_url = (provider.config or {}).get('payment_url') or row.checkout_url

            row.checkout_url = checkout_url
            row.updated_at = now
            row.meta = {
                **metadata,
                'payment_provider_id': provider.id,
                'payment_provider_name': provider.name,
                'payment_provider_type': provider.provider_type,
            }
            await db.commit()
            await db.refresh(row)
            model = SubscriptionCheckoutModel.model_validate(row)
            model.plan = plan
            return model

    async def complete_epay_checkout(
        self, provider_id: str, params: dict, db: Optional[AsyncSession] = None
    ) -> SubscriptionCheckoutModel:
        provider = await self.get_payment_provider_by_id(provider_id, db=db)
        if not provider or provider.provider_type != 'epay':
            raise ValueError('Payment provider not found')
        key = str((provider.config or {}).get('key') or '')
        if not key or self.build_epay_sign(params, key) != params.get('sign'):
            raise ValueError('Invalid payment signature')
        if params.get('trade_status') != 'TRADE_SUCCESS':
            raise ValueError('Payment is not successful')
        checkout_id = str(params.get('out_trade_no') or '')
        checkout = await self.get_checkout(checkout_id, db=db)
        if not checkout:
            raise ValueError('Subscription checkout not found')
        if f'{float(checkout.amount):.2f}' != f'{float(params.get("money") or 0):.2f}':
            raise ValueError('Payment amount mismatch')
        return await self.complete_checkout(
            checkout_id,
            metadata={
                'provider_id': provider.id,
                'provider_type': provider.provider_type,
                'trade_no': params.get('trade_no'),
                'source': 'epay_notify',
            },
            db=db,
        )

    async def get_checkout(
        self, checkout_id: str, user_id: Optional[str] = None, db: Optional[AsyncSession] = None
    ) -> Optional[SubscriptionCheckoutModel]:
        async with get_async_db_context(db) as db:
            stmt = select(SubscriptionCheckout).where(SubscriptionCheckout.id == checkout_id)
            if user_id:
                stmt = stmt.where(SubscriptionCheckout.user_id == user_id)
            row = (await db.execute(stmt)).scalar_one_or_none()
            if not row:
                return None
            model = SubscriptionCheckoutModel.model_validate(row)
            model.plan = await self.get_plan_by_id(row.plan_id, db=db)
            return model

    async def get_checkouts(
        self, status: Optional[str] = None, db: Optional[AsyncSession] = None
    ) -> list[SubscriptionCheckoutModel]:
        async with get_async_db_context(db) as db:
            stmt = select(SubscriptionCheckout).order_by(SubscriptionCheckout.created_at.desc()).limit(100)
            if status:
                stmt = stmt.where(SubscriptionCheckout.status == status)
            rows = (await db.execute(stmt)).scalars().all()
            plans = {plan.id: plan for plan in await self.get_plans(active_only=False, db=db)}
            result = []
            for row in rows:
                model = SubscriptionCheckoutModel.model_validate(row)
                model.plan = plans.get(row.plan_id)
                result.append(model)
            return result

    async def complete_checkout(
        self, checkout_id: str, metadata: Optional[dict] = None, db: Optional[AsyncSession] = None
    ) -> SubscriptionCheckoutModel:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            row = await db.get(SubscriptionCheckout, checkout_id)
            if not row:
                raise ValueError('Subscription checkout not found')
            if row.status == 'paid':
                model = SubscriptionCheckoutModel.model_validate(row)
                model.plan = await self.get_plan_by_id(row.plan_id, db=db)
                return model
            row.status = 'paid'
            row.completed_at = now
            row.updated_at = now
            row.meta = {**(row.meta or {}), **(metadata or {})}
            await db.commit()
            await db.refresh(row)
            plan = await self.get_plan_by_id(row.plan_id, db=db)
            period_end = now + 30 * 24 * 60 * 60
            await self.set_user_subscription(
                UserSubscriptionForm(
                    user_id=row.user_id,
                    plan_id=row.plan_id,
                    current_period_start=now,
                    current_period_end=period_end,
                    metadata={'checkout_id': row.id, 'source': 'checkout'},
                ),
                db=db,
            )
            model = SubscriptionCheckoutModel.model_validate(row)
            model.plan = plan
            return model

    async def upsert_plan(self, form: SubscriptionPlanForm, db: Optional[AsyncSession] = None) -> SubscriptionPlanModel:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            row = await db.get(SubscriptionPlan, form.id)
            if row:
                for key, value in form.model_dump().items():
                    setattr(row, key, value)
                row.updated_at = now
            else:
                row = SubscriptionPlan(**form.model_dump(), created_at=now, updated_at=now)
                db.add(row)
            await db.commit()
            await db.refresh(row)
            return SubscriptionPlanModel.model_validate(row)

    async def set_user_subscription(
        self, form: UserSubscriptionForm, db: Optional[AsyncSession] = None
    ) -> UserSubscriptionModel:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            await db.execute(
                delete(UserSubscription)
                .where(UserSubscription.user_id == form.user_id)
                .where(UserSubscription.status == 'active')
            )
            row = UserSubscription(
                id=str(uuid4()),
                user_id=form.user_id,
                plan_id=form.plan_id,
                status=form.status,
                current_period_end=form.current_period_end,
                meta=form.metadata,
                current_period_start=form.current_period_start or now,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return UserSubscriptionModel.model_validate(row)

    async def get_user_subscription(
        self, user_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[UserSubscriptionModel]:
        now = int(time.time())
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(UserSubscription)
                .where(UserSubscription.user_id == user_id)
                .where(UserSubscription.status == 'active')
                .where((UserSubscription.current_period_end == None) | (UserSubscription.current_period_end > now))
                .order_by(UserSubscription.created_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            return UserSubscriptionModel.model_validate(row) if row else None

    async def get_user_plan(
        self, user_id: str, db: Optional[AsyncSession] = None
    ) -> tuple[SubscriptionPlanModel, Optional[UserSubscriptionModel]]:
        subscription = await self.get_user_subscription(user_id, db=db)
        plan_id = subscription.plan_id if subscription else DEFAULT_PLAN_ID
        plan = await self.get_plan_by_id(plan_id, db=db) or await self.get_plan_by_id(DEFAULT_PLAN_ID, db=db)
        return plan, subscription


Subscriptions = SubscriptionsTable()
SubscriptionUsage = SubscriptionUsageTable()
