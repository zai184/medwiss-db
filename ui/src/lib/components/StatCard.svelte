<script lang="ts">
  import type { ComponentType } from 'svelte';
  
  interface Props {
    title: string;
    value: number | string;
    icon?: ComponentType;
    trend?: number;
    color?: 'blue' | 'green' | 'purple' | 'orange' | 'red';
  }

  let { title, value, icon, trend, color = 'blue' }: Props = $props();

  const colorClasses = {
    blue: {
      bg: 'bg-blue-50',
      text: 'text-blue-700',
      iconBg: 'bg-blue-100',
      trendUp: 'text-blue-600',
      trendDown: 'text-blue-400'
    },
    green: {
      bg: 'bg-emerald-50',
      text: 'text-emerald-700',
      iconBg: 'bg-emerald-100',
      trendUp: 'text-emerald-600',
      trendDown: 'text-emerald-400'
    },
    purple: {
      bg: 'bg-violet-50',
      text: 'text-violet-700',
      iconBg: 'bg-violet-100',
      trendUp: 'text-violet-600',
      trendDown: 'text-violet-400'
    },
    orange: {
      bg: 'bg-amber-50',
      text: 'text-amber-700',
      iconBg: 'bg-amber-100',
      trendUp: 'text-amber-600',
      trendDown: 'text-amber-400'
    },
    red: {
      bg: 'bg-rose-50',
      text: 'text-rose-700',
      iconBg: 'bg-rose-100',
      trendUp: 'text-rose-600',
      trendDown: 'text-rose-400'
    }
  };

  const colors = $derived(colorClasses[color]);
</script>

<div class="{colors.bg} rounded-xl p-6 transition-all duration-300 hover:shadow-lg hover:scale-[1.02]">
  <div class="flex items-start justify-between">
    <div class="flex-1">
      <p class="text-sm font-medium {colors.text} opacity-80 uppercase tracking-wider">
        {title}
      </p>
      <p class="mt-2 text-3xl font-bold {colors.text}">
        {typeof value === 'number' ? value.toLocaleString('de-DE') : value}
      </p>
      {#if trend !== undefined}
        <p class="mt-1 text-sm flex items-center gap-1">
          <span class={trend >= 0 ? colors.trendUp : colors.trendDown}>
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
          </span>
          <span class="text-gray-500">vs. letzte Woche</span>
        </p>
      {/if}
    </div>
    {#if icon}
      {@const Icon = icon}
      <div class="{colors.iconBg} rounded-lg p-3">
        <Icon class="w-6 h-6 {colors.text}" />
      </div>
    {/if}
  </div>
</div>
