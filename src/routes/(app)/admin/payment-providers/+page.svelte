<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getAdminSubscriptionPaymentProviders,
		upsertSubscriptionPaymentProvider,
		type SubscriptionPaymentProvider
	} from '$lib/apis/subscriptions';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let providers: SubscriptionPaymentProvider[] = [];
	let selectedProviderId = '';
	let configText = '';
	let saving = false;

	$: selectedProvider = providers.find((provider) => provider.id === selectedProviderId) ?? null;

	const defaultProvider = (): SubscriptionPaymentProvider => ({
		id: `epay-${Date.now()}`,
		name: 'ePay',
		provider_type: 'epay',
		config: {
			api_url: 'https://ezfp.cn',
			pid: '',
			key: '',
			pay_type: 'alipay',
			sitename: 'new-webui'
		},
		is_active: true,
		sort_order: providers.length * 10
	});

	const load = async () => {
		providers = await getAdminSubscriptionPaymentProviders(localStorage.token);
		if (!providers.length) {
			providers = [defaultProvider()];
		}
		selectedProviderId = providers[0]?.id ?? '';
		configText = JSON.stringify(providers[0]?.config ?? {}, null, 2);
	};

	const selectProvider = (provider: SubscriptionPaymentProvider) => {
		selectedProviderId = provider.id;
		configText = JSON.stringify(provider.config ?? {}, null, 2);
	};

	const addProvider = () => {
		const provider = defaultProvider();
		providers = [...providers, provider];
		selectProvider(provider);
	};

	const updateField = (
		key: keyof SubscriptionPaymentProvider,
		value: string | number | boolean
	) => {
		providers = providers.map((provider) =>
			provider.id === selectedProviderId ? { ...provider, [key]: value } : provider
		);
	};

	const save = async () => {
		if (!selectedProvider) return;
		saving = true;
		try {
			const config = JSON.parse(configText || '{}');
			const saved = await upsertSubscriptionPaymentProvider(localStorage.token, {
				...selectedProvider,
				config
			});
			providers = providers.some((provider) => provider.id === saved.id)
				? providers.map((provider) => (provider.id === saved.id ? saved : provider))
				: [...providers, saved];
			configText = JSON.stringify(saved.config ?? {}, null, 2);
			toast.success($i18n.t('Payment provider saved'));
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
			{#each providers as provider}
				<button
					type="button"
					class="w-full rounded-xl px-3 py-2 text-left text-sm transition {selectedProviderId ===
					provider.id
						? 'bg-gray-100 dark:bg-gray-850'
						: 'hover:bg-gray-50 dark:hover:bg-gray-850/50'}"
					on:click={() => selectProvider(provider)}
				>
					<div class="font-medium">{provider.name}</div>
					<div class="text-xs text-gray-500">{provider.provider_type}</div>
				</button>
			{/each}
			<button
				type="button"
				class="mt-2 w-full rounded-xl border border-dashed border-gray-200 px-3 py-2 text-left text-sm text-gray-500 dark:border-gray-800"
				on:click={addProvider}
			>
				{$i18n.t('Add payment provider')}
			</button>
		</aside>

		{#if selectedProvider}
			<section
				class="flex min-w-0 flex-1 flex-col rounded-2xl border border-gray-100 bg-white p-5 dark:border-gray-800 dark:bg-gray-900"
			>
				<div class="flex items-center justify-between">
					<div>
						<div class="text-lg font-semibold">{$i18n.t('Payment Provider')}</div>
						<div class="text-sm text-gray-500">
							{$i18n.t('Configure payment channels shown on the order page.')}
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

				<div class="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
					<label class="text-sm">
						<div class="mb-1 text-xs text-gray-500">ID</div>
						<input
							class="w-full rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-850"
							value={selectedProvider.id}
							on:input={(e) => updateField('id', e.currentTarget.value)}
						/>
					</label>
					<label class="text-sm">
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>
						<input
							class="w-full rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-850"
							value={selectedProvider.name}
							on:input={(e) => updateField('name', e.currentTarget.value)}
						/>
					</label>
					<label class="text-sm">
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Type')}</div>
						<select
							class="w-full rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-850"
							value={selectedProvider.provider_type}
							on:change={(e) => updateField('provider_type', e.currentTarget.value)}
						>
							<option value="epay">ePay</option>
							<option value="manual">Manual</option>
						</select>
					</label>
					<label class="text-sm">
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Sort Order')}</div>
						<input
							type="number"
							class="w-full rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-850"
							value={selectedProvider.sort_order ?? 0}
							on:input={(e) => updateField('sort_order', Number(e.currentTarget.value))}
						/>
					</label>
				</div>

				<label class="mt-4 flex items-center gap-2 text-sm">
					<input
						type="checkbox"
						checked={selectedProvider.is_active ?? true}
						on:change={(e) => updateField('is_active', e.currentTarget.checked)}
					/>
					<span>{$i18n.t('Active')}</span>
				</label>

				<label class="mt-4 flex min-h-0 flex-1 flex-col text-sm">
					<div class="mb-1 text-xs text-gray-500">{$i18n.t('Config JSON')}</div>
					<textarea
						class="min-h-96 flex-1 rounded-xl border border-gray-100 bg-gray-950 px-3 py-2 font-mono text-xs text-gray-100 dark:border-gray-800"
						bind:value={configText}
						spellcheck="false"
					></textarea>
				</label>
			</section>
		{/if}
	</div>
{/if}
