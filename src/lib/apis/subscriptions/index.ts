import { WEBUI_API_BASE_URL } from '$lib/constants';

export type SubscriptionPlan = {
	id: string;
	name: string;
	description?: string;
	price: number;
	currency: string;
	interval: string;
	features: string[];
	rules: Record<string, any>;
	is_active: boolean;
	sort_order: number;
	created_at: number;
	updated_at: number;
};

export type UsageSummary = {
	message_count: number;
	input_tokens: number;
	output_tokens: number;
	total_tokens: number;
	amount: number;
};

export type SubscriptionStatus = {
	plan: SubscriptionPlan;
	subscription: Record<string, any> | null;
	usage_5h: UsageSummary;
	usage_week: UsageSummary;
};

const apiFetch = async (token: string, path: string, options: RequestInit = {}) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/subscriptions${path}`, {
		...options,
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`,
			...(options.headers ?? {})
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSubscriptionPlans = async (token: string): Promise<SubscriptionPlan[]> => {
	return await apiFetch(token, '/plans');
};

export const getSubscriptionStatus = async (token: string): Promise<SubscriptionStatus> => {
	return await apiFetch(token, '/status');
};

export const selectSubscriptionPlan = async (token: string, planId: string) => {
	return await apiFetch(token, `/select/${encodeURIComponent(planId)}`, { method: 'POST' });
};

export const upsertSubscriptionPlan = async (token: string, plan: Partial<SubscriptionPlan>) => {
	return await apiFetch(token, '/plans/upsert', {
		method: 'POST',
		body: JSON.stringify(plan)
	});
};
