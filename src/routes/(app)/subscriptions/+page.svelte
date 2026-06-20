<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { WEBUI_NAME, models, showSidebar } from '$lib/stores';
	import {
		getSubscriptionPlans,
		getSubscriptionStatus,
		selectSubscriptionPlan,
		type SubscriptionPlan,
		type SubscriptionStatus
	} from '$lib/apis/subscriptions';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let plans: SubscriptionPlan[] = [];
	let status: SubscriptionStatus | null = null;
	let selectingPlanId = '';

	const formatPrice = (plan: SubscriptionPlan) => {
		return new Intl.NumberFormat(undefined, {
			style: 'currency',
			currency: plan.currency || 'USD',
			maximumFractionDigits: 0
		}).format(plan.price ?? 0);
	};

	const formatNumber = (value: number) => {
		return new Intl.NumberFormat().format(value ?? 0);
	};

	const modelNames = (plan: SubscriptionPlan) => {
		const ids = plan.rules?.allowed_model_ids ?? [];
		if (!ids.length) return $i18n.t('All available models');
		return ids
			.map((id) => $models.find((model) => model.id === id)?.name ?? id)
			.slice(0, 4)
			.join(', ');
	};

	const usagePercent = (used: number, limit?: number) => {
		if (!limit || limit <= 0) return 0;
		return Math.min(100, Math.round((used / limit) * 100));
	};

	const refresh = async () => {
		const token = localStorage.token;
		[plans, status] = await Promise.all([getSubscriptionPlans(token), getSubscriptionStatus(token)]);
	};

	const selectPlan = async (plan: SubscriptionPlan) => {
		if (plan.id === status?.plan?.id) return;
		selectingPlanId = plan.id;
		try {
			await selectSubscriptionPlan(localStorage.token, plan.id);
			await refresh();
			toast.success($i18n.t('Subscription updated'));
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			selectingPlanId = '';
		}
	};

	onMount(async () => {
		await refresh();
		loaded = true;
	});
</script>

<svelte:head>
	<title>{$i18n.t('Subscriptions')} - {$WEBUI_NAME}</title>
</svelte:head>

<div
	class="relative flex flex-col w-full min-h-screen transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full bg-gray-50 dark:bg-gray-950"
>
	<div class="sticky top-0 z-10 flex items-center justify-between px-5 py-4 bg-gray-50/90 dark:bg-gray-950/90 backdrop-blur">
		<div>
			<div class="text-xl font-semibold text-gray-900 dark:text-gray-50">
				{$i18n.t('Subscriptions')}
			</div>
			<div class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('Choose model access and usage limits for your account.')}
			</div>
		</div>
		<a
			href="/"
			class="flex size-9 items-center justify-center rounded-full hover:bg-gray-100 dark:hover:bg-gray-900"
			aria-label={$i18n.t('Close')}
		>
			<XMark className="size-5" strokeWidth="1.8" />
		</a>
	</div>

	{#if !loaded}
		<div class="flex flex-1 items-center justify-center">
			<Spinner />
		</div>
	{:else}
		<div class="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-5 pb-10">
			{#if status}
				<div class="grid grid-cols-1 gap-3 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900 md:grid-cols-3">
					<div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Current plan')}</div>
						<div class="mt-1 text-lg font-semibold text-gray-900 dark:text-gray-50">
							{status.plan.name}
						</div>
					</div>
					<div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Weekly messages')}</div>
						<div class="mt-2 h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
							<div
								class="h-full rounded-full bg-gray-900 dark:bg-gray-100"
								style="width: {usagePercent(status.usage_week.message_count, status.plan.rules?.message_limit_per_week)}%"
							/>
						</div>
						<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
							{formatNumber(status.usage_week.message_count)} / {status.plan.rules?.message_limit_per_week ?? '∞'}
						</div>
					</div>
					<div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Weekly tokens')}</div>
						<div class="mt-2 h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
							<div
								class="h-full rounded-full bg-indigo-600"
								style="width: {usagePercent(status.usage_week.total_tokens, status.plan.rules?.token_limit_per_week)}%"
							/>
						</div>
						<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
							{formatNumber(status.usage_week.total_tokens)} / {status.plan.rules?.token_limit_per_week
								? formatNumber(status.plan.rules.token_limit_per_week)
								: '∞'}
						</div>
					</div>
				</div>
			{/if}

			<div class="grid grid-cols-1 gap-5 lg:grid-cols-4">
				{#each plans as plan}
					{@const isCurrent = plan.id === status?.plan?.id}
					<section
						class="flex min-h-[640px] flex-col rounded-xl border bg-white p-6 shadow-sm dark:bg-gray-900 {isCurrent
							? 'border-indigo-300 bg-indigo-50/60 dark:border-indigo-700 dark:bg-indigo-950/20'
							: 'border-gray-200 dark:border-gray-800'}"
					>
						<div class="flex items-start justify-between gap-3">
							<div class="text-2xl font-semibold text-gray-900 dark:text-gray-50">{plan.name}</div>
							{#if isCurrent}
								<div class="rounded-full bg-indigo-100 px-2 py-1 text-xs font-medium text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200">
									{$i18n.t('Current')}
								</div>
							{/if}
						</div>

						<div class="mt-8 flex items-end gap-1 text-gray-900 dark:text-gray-50">
							<span class="text-5xl font-semibold tracking-normal">{formatPrice(plan)}</span>
							<span class="pb-2 text-xs text-gray-500 dark:text-gray-400">/ {$i18n.t(plan.interval)}</span>
						</div>

						<div class="mt-5 min-h-10 text-sm text-gray-700 dark:text-gray-300">
							{plan.description}
						</div>

						<button
							type="button"
							class="mt-5 h-11 rounded-full px-4 text-sm font-semibold transition {isCurrent
								? 'border border-gray-200 bg-white text-gray-500 dark:border-gray-700 dark:bg-gray-900'
								: plan.id === 'plus'
									? 'bg-indigo-600 text-white hover:bg-indigo-500'
									: 'bg-gray-950 text-white hover:bg-gray-800 dark:bg-white dark:text-gray-950'}"
							disabled={isCurrent || selectingPlanId === plan.id}
							on:click={() => selectPlan(plan)}
						>
							{#if selectingPlanId === plan.id}
								{$i18n.t('Updating...')}
							{:else if isCurrent}
								{$i18n.t('Your current plan')}
							{:else}
								{$i18n.t('Select')} {plan.name}
							{/if}
						</button>

						<div class="mt-7 space-y-4 text-sm">
							<div class="flex gap-3">
								<Check className="mt-0.5 size-4 shrink-0" strokeWidth="2" />
								<span>{modelNames(plan)}</span>
							</div>
							{#each plan.features ?? [] as feature}
								<div class="flex gap-3">
									<Check className="mt-0.5 size-4 shrink-0" strokeWidth="2" />
									<span>{feature}</span>
								</div>
							{/each}
							<div class="flex gap-3">
								<Check className="mt-0.5 size-4 shrink-0" strokeWidth="2" />
								<span>
									{$i18n.t('Messages')}: {plan.rules?.message_limit_per_5h ?? '∞'} / 5h,
									{plan.rules?.message_limit_per_week ?? '∞'} / {$i18n.t('week')}
								</span>
							</div>
							<div class="flex gap-3">
								<Check className="mt-0.5 size-4 shrink-0" strokeWidth="2" />
								<span>
									{$i18n.t('Tokens')}: {plan.rules?.token_limit_per_week
										? formatNumber(plan.rules.token_limit_per_week)
										: '∞'} / {$i18n.t('week')}
								</span>
							</div>
							<div class="flex gap-3">
								<Check className="mt-0.5 size-4 shrink-0" strokeWidth="2" />
								<span>
									{$i18n.t('Spend limit')}: {plan.rules?.amount_limit_per_5h ?? '∞'} / 5h,
									{plan.rules?.amount_limit_per_week ?? '∞'} / {$i18n.t('week')}
								</span>
							</div>
						</div>

						<div class="mt-auto pt-8 text-xs leading-5 text-gray-500 dark:text-gray-400">
							{$i18n.t('Model access and usage limits are enforced before every chat request.')}
						</div>
					</section>
				{/each}
			</div>
		</div>
	{/if}
</div>
