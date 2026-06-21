<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		goto(`/orders/${$page.params.id}`, { replaceState: true });
	});
</script>
