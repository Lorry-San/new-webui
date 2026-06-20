import logging
import time
from typing import Optional
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
        return round((input_tokens / 1000 * float(input_price or 0)) + (output_tokens / 1000 * float(output_price or 0)), 6)

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
    async def ensure_default_plans(self, db: Optional[AsyncSession] = None) -> None:
        async with get_async_db_context(db) as db:
            count = (await db.execute(select(func.count()).select_from(SubscriptionPlan))).scalar() or 0
            if count > 0:
                return
            now = int(time.time())
            for plan in DEFAULT_PLANS:
                db.add(SubscriptionPlan(**plan, is_active=True, created_at=now, updated_at=now))
            await db.commit()

    async def get_plans(self, active_only: bool = True, db: Optional[AsyncSession] = None) -> list[SubscriptionPlanModel]:
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
                .where(
                    (UserSubscription.current_period_end == None)
                    | (UserSubscription.current_period_end > now)
                )
                .order_by(UserSubscription.created_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            return UserSubscriptionModel.model_validate(row) if row else None

    async def get_user_plan(self, user_id: str, db: Optional[AsyncSession] = None) -> tuple[SubscriptionPlanModel, Optional[UserSubscriptionModel]]:
        subscription = await self.get_user_subscription(user_id, db=db)
        plan_id = subscription.plan_id if subscription else DEFAULT_PLAN_ID
        plan = await self.get_plan_by_id(plan_id, db=db) or await self.get_plan_by_id(DEFAULT_PLAN_ID, db=db)
        return plan, subscription


Subscriptions = SubscriptionsTable()
SubscriptionUsage = SubscriptionUsageTable()
