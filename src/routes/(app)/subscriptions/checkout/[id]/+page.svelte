<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';

	import { WEBUI_NAME, showSidebar } from '$lib/stores';
	import { getSubscriptionCheckout, type SubscriptionCheckout } from '$lib/apis/subscriptions';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let refreshing = false;
	let checkout: SubscriptionCheckout | null = null;

	const formatPrice = (amount = 0, currency = 'USD') => {
		return new Intl.NumberFormat(undefined, {
			style: 'currency',
			currency,
			maximumFractionDigits: 0
		}).format(amount);
	};

	const load = async () => {
		checkout = await getSubscriptionCheckout(localStorage.token, $page.params.id);
	};

	const refresh = async () => {
		refreshing = true;
		try {
			await load();
			if (checkout?.status === 'paid') {
				toast.success($i18n.t('Subscription activated'));
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			refreshing = false;
		}
	};

	onMount(async () => {
		try {
			await load();
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loaded = true;
		}
	});
</script>

<svelte:head>
	<title>{$i18n.t('Checkout')} - {$WEBUI_NAME}</title>
</svelte:head>

<div
	class="relative flex min-h-screen w-full flex-col bg-gray-50 transition-width duration-200 ease-in-out dark:bg-gray-950 {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<div
		class="sticky top-0 z-10 flex items-center justify-between bg-gray-50/90 px-5 py-4 backdrop-blur dark:bg-gray-950/90"
	>
		<div>
			<div class="text-xl font-semibold text-gray-900 dark:text-gray-50">
				{$i18n.t('Checkout')}
			</div>
			<div class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('Complete payment to activate your subscription.')}
			</div>
		</div>
		<a
			href="/subscriptions"
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
	{:else if checkout}
		<div class="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-5 pb-12">
			<section class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
				<div class="flex flex-wrap items-start justify-between gap-4">
					<div>
						<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Plan')}</div>
						<div class="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-50">
							{checkout.plan?.name ?? checkout.plan_id}
						</div>
					</div>
					<div
						class="rounded-full px-3 py-1 text-xs font-medium {checkout.status === 'paid'
							? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-200'
							: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-100'}"
					>
						{checkout.status}
					</div>
				</div>

				<div class="mt-7 grid grid-cols-1 gap-3 rounded-xl bg-gray-50 p-4 text-sm dark:bg-gray-950 md:grid-cols-2">
					<div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Amount')}</div>
						<div class="mt-1 font-semibold text-gray-900 dark:text-gray-50">
							{formatPrice(checkout.amount, checkout.currency)} / {$i18n.t(checkout.interval)}
						</div>
					</div>
					<div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Order ID')}</div>
						<div class="mt-1 break-all font-mono text-xs text-gray-700 dark:text-gray-300">
							{checkout.id}
						</div>
					</div>
				</div>

				{#if checkout.status === 'paid'}
					<div
						class="mt-6 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800 dark:border-green-900 dark:bg-green-950/30 dark:text-green-100"
					>
						{$i18n.t('Payment confirmed. Your subscription is active.')}
					</div>
					<a
						href="/"
						class="mt-6 inline-flex h-11 items-center justify-center rounded-full bg-gray-950 px-5 text-sm font-semibold text-white dark:bg-white dark:text-gray-950"
					>
						{$i18n.t('Start chatting')}
					</a>
				{:else}
					<div
						class="mt-6 rounded-xl border border-gray-200 p-4 text-sm text-gray-700 dark:border-gray-800 dark:text-gray-300"
					>
						{#if checkout.checkout_url}
							{$i18n.t('Open the payment link, then return here after payment.')}
						{:else}
							{$i18n.t('This order is waiting for administrator payment confirmation.')}
						{/if}
					</div>
					<div class="mt-6 flex flex-wrap gap-3">
						{#if checkout.checkout_url}
							<a
								href={checkout.checkout_url}
								target="_blank"
								rel="noreferrer"
								class="inline-flex h-11 items-center justify-center rounded-full bg-gray-950 px-5 text-sm font-semibold text-white dark:bg-white dark:text-gray-950"
							>
								{$i18n.t('Pay now')}
							</a>
						{/if}
						<button
							type="button"
							class="inline-flex h-11 items-center justify-center rounded-full border border-gray-200 px-5 text-sm font-semibold text-gray-900 disabled:opacity-50 dark:border-gray-700 dark:text-gray-100"
							disabled={refreshing}
							on:click={refresh}
						>
							{refreshing ? $i18n.t('Checking...') : $i18n.t('Check status')}
						</button>
					</div>
				{/if}
			</section>
		</div>
	{/if}
</div>
