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

export type SubscriptionCheckout = {
	id: string;
	user_id: string;
	plan_id: string;
	status: string;
	amount: number;
	currency: string;
	interval: string;
	checkout_url?: string | null;
	metadata?: Record<string, any> | null;
	created_at: number;
	updated_at: number;
	completed_at?: number | null;
	plan?: SubscriptionPlan | null;
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

export const createSubscriptionCheckout = async (
	token: string,
	planId: string
): Promise<SubscriptionCheckout> => {
	return await apiFetch(token, `/checkout/${encodeURIComponent(planId)}`, { method: 'POST' });
};

export const getSubscriptionCheckout = async (
	token: string,
	checkoutId: string
): Promise<SubscriptionCheckout> => {
	return await apiFetch(token, `/checkout/${encodeURIComponent(checkoutId)}`);
};

export const getSubscriptionCheckouts = async (
	token: string,
	statusFilter = ''
): Promise<SubscriptionCheckout[]> => {
	const query = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : '';
	return await apiFetch(token, `/checkouts${query}`);
};

export const confirmSubscriptionCheckout = async (
	token: string,
	checkoutId: string
): Promise<SubscriptionCheckout> => {
	return await apiFetch(token, `/checkouts/${encodeURIComponent(checkoutId)}/confirm`, {
		method: 'POST'
	});
};

export const upsertSubscriptionPlan = async (token: string, plan: Partial<SubscriptionPlan>) => {
	return await apiFetch(token, '/plans/upsert', {
		method: 'POST',
		body: JSON.stringify(plan)
	});
};
