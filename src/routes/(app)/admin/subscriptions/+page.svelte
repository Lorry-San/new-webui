<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		confirmSubscriptionCheckout,
		getSubscriptionCheckouts,
		getSubscriptionPlans,
		upsertSubscriptionPlan,
		type SubscriptionCheckout,
		type SubscriptionPlan
	} from '$lib/apis/subscriptions';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let plans: SubscriptionPlan[] = [];
	let checkouts: SubscriptionCheckout[] = [];
	let selectedPlanId = '';
	let rulesText = '';
	let saving = false;
	let confirmingCheckoutId = '';

	$: selectedPlan = plans.find((plan) => plan.id === selectedPlanId) ?? null;

	const load = async () => {
		[plans, checkouts] = await Promise.all([
			getSubscriptionPlans(localStorage.token),
			getSubscriptionCheckouts(localStorage.token, 'pending')
		]);
		selectedPlanId = plans[0]?.id ?? '';
		rulesText = JSON.stringify(plans[0]?.rules ?? {}, null, 2);
	};

	const formatPrice = (amount = 0, currency = 'USD') => {
		return new Intl.NumberFormat(undefined, {
			style: 'currency',
			currency,
			maximumFractionDigits: 0
		}).format(amount);
	};

	const confirmCheckout = async (checkout: SubscriptionCheckout) => {
		confirmingCheckoutId = checkout.id;
		try {
			await confirmSubscriptionCheckout(localStorage.token, checkout.id);
			checkouts = await getSubscriptionCheckouts(localStorage.token, 'pending');
			toast.success($i18n.t('Checkout confirmed'));
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			confirmingCheckoutId = '';
		}
	};

	const selectPlan = (plan: SubscriptionPlan) => {
		selectedPlanId = plan.id;
		rulesText = JSON.stringify(plan.rules ?? {}, null, 2);
	};

	const updateField = (key: keyof SubscriptionPlan, value: string | number | boolean) => {
		plans = plans.map((plan) => (plan.id === selectedPlanId ? { ...plan, [key]: value } : plan));
	};

	const updateFeatures = (value: string) => {
		plans = plans.map((plan) =>
			plan.id === selectedPlanId
				? {
						...plan,
						features: value
							.split('\n')
							.map((item) => item.trim())
							.filter(Boolean)
					}
				: plan
		);
	};

	const save = async () => {
		if (!selectedPlan) return;
		saving = true;
		try {
			const rules = JSON.parse(rulesText || '{}');
			const saved = await upsertSubscriptionPlan(localStorage.token, { ...selectedPlan, rules });
			plans = plans.map((plan) => (plan.id === saved.id ? saved : plan));
			rulesText = JSON.stringify(saved.rules ?? {}, null, 2);
			toast.success($i18n.t('Subscription plan saved'));
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			saving = false;
		}
	};

	onMount(async () => {
		await load();
		loaded = true;
	});
</script>

{#if !loaded}
	<div class="flex h-full items-center justify-center">
		<Spinner />
	</div>
{:else}
	<div class="mx-auto flex h-full max-w-6xl gap-4 px-4 py-4">
		<aside
			class="w-64 shrink-0 rounded-2xl border border-gray-100 bg-white p-2 dark:border-gray-800 dark:bg-gray-900"
		>
			{#each plans as plan}
				<button
					type="button"
					class="w-full rounded-xl px-3 py-2 text-left text-sm transition {selectedPlanId ===
					plan.id
						? 'bg-gray-100 dark:bg-gray-850'
						: 'hover:bg-gray-50 dark:hover:bg-gray-850/50'}"
					on:click={() => selectPlan(plan)}
				>
					<div class="font-medium">{plan.name}</div>
					<div class="text-xs text-gray-500">{plan.id}</div>
				</button>
			{/each}
		</aside>

		{#if selectedPlan}
			<section
				class="flex min-w-0 flex-1 flex-col rounded-2xl border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900"
			>
				<div class="flex items-center justify-between">
					<div>
						<div class="text-lg font-semibold">{$i18n.t('Subscription Plan')}</div>
						<div class="text-sm text-gray-500">
							{$i18n.t('Configure model access, usage limits, token prices, and spend windows.')}
						</div>
					</div>
					<button
						type="button"
						class="rounded-full bg-gray-950 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-gray-950"
						disabled={saving}
						on:click={save}
					>
						{saving ? $i18n.t('Saving...') : $i18n.t('Save')}
					</button>
				</div>

				<div
					class="mt-5 rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-950"
				>
					<div class="flex items-center justify-between gap-3">
						<div>
							<div class="text-sm font-semibold">{$i18n.t('Pending Checkouts')}</div>
							<div class="text-xs text-gray-500">
								{$i18n.t('Confirm paid orders to activate subscriptions.')}
							</div>
						</div>
						<button
							type="button"
							class="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-medium dark:border-gray-700"
							on:click={async () =>
								(checkouts = await getSubscriptionCheckouts(localStorage.token, 'pending'))}
						>
							{$i18n.t('Refresh')}
						</button>
					</div>

					{#if checkouts.length === 0}
						<div class="mt-3 text-sm text-gray-500">{$i18n.t('No pending checkouts.')}</div>
					{:else}
						<div class="mt-3 max-h-56 space-y-2 overflow-auto">
							{#each checkouts as checkout}
								<div
									class="rounded-xl border border-gray-100 bg-white p-3 text-sm dark:border-gray-800 dark:bg-gray-900"
								>
									<div class="flex flex-wrap items-center justify-between gap-3">
										<div class="min-w-0">
											<div class="font-medium">
												{checkout.plan?.name ?? checkout.plan_id}
												<span class="text-gray-500">
													{formatPrice(checkout.amount, checkout.currency)}
												</span>
											</div>
											<div class="mt-1 break-all font-mono text-xs text-gray-500">
												{checkout.id}
											</div>
											<div class="mt-1 break-all text-xs text-gray-500">
												{$i18n.t('User')}: {checkout.user_id}
											</div>
										</div>
										<button
											type="button"
											class="h-9 shrink-0 rounded-full bg-gray-950 px-3 text-xs font-semibold text-white disabled:opacity-50 dark:bg-white dark:text-gray-950"
											disabled={confirmingCheckoutId === checkout.id}
											on:click={() => confirmCheckout(checkout)}
										>
											{confirmingCheckoutId === checkout.id
												? $i18n.t('Confirming...')
												: $i18n.t('Confirm paid')}
										</button>
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<div class="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
					<label class="text-sm">
						<div class="mb-1 text-xs text-gray-500">ID</div>
						<input
							class="w-full rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-850"
							value={selectedPlan.id}
							disabled
						/>
					</label>
					<label class="text-sm">
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>
						<input
							class="w-full rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-850"
							value={selectedPlan.name}
							on:input={(e) => updateField('name', e.currentTarget.value)}
						/>
					</label>
					<label class="text-sm">
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Price')}</div>
						<input
							type="number"
							class="w-full rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-850"
							value={selectedPlan.price}
							on:input={(e) => updateField('price', Number(e.currentTarget.value))}
						/>
					</label>
					<label class="text-sm">
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Currency')}</div>
						<input
							class="w-full rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-850"
							value={selectedPlan.currency}
							on:input={(e) => updateField('currency', e.currentTarget.value)}
						/>
					</label>
				</div>

				<label class="mt-4 text-sm">
					<div class="mb-1 text-xs text-gray-500">{$i18n.t('Description')}</div>
					<textarea
						class="min-h-20 w-full rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-850"
						value={selectedPlan.description ?? ''}
						on:input={(e) => updateField('description', e.currentTarget.value)}
					/>
				</label>

				<label class="mt-4 text-sm">
					<div class="mb-1 text-xs text-gray-500">{$i18n.t('Features')}</div>
					<textarea
						class="min-h-28 w-full rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-850"
						value={(selectedPlan.features ?? []).join('\n')}
						on:input={(e) => updateFeatures(e.currentTarget.value)}
					/>
				</label>

				<label class="mt-4 flex min-h-0 flex-1 flex-col text-sm">
					<div class="mb-1 text-xs text-gray-500">{$i18n.t('Rules JSON')}</div>
					<textarea
						class="min-h-72 flex-1 rounded-xl border border-gray-100 bg-gray-950 px-3 py-2 font-mono text-xs text-gray-100 dark:border-gray-800"
						bind:value={rulesText}
						spellcheck="false"
					/>
				</label>
			</section>
		{/if}
	</div>
{/if}
