<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import Chart from 'chart.js/auto';
  import type { FachStats } from '$lib/api';
  
  interface Props {
    data: FachStats[];
  }

  let { data }: Props = $props();
  
  let canvas: HTMLCanvasElement;
  let chart: Chart | null = null;

  const colors = [
    '#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444',
    '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6366f1'
  ];

  function createChart() {
    if (!canvas || data.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Sort by count descending and take top 8
    const sortedData = [...data].sort((a, b) => b.count - a.count).slice(0, 8);

    chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: sortedData.map(d => d.fachgebiet_name),
        datasets: [{
          data: sortedData.map(d => d.count),
          backgroundColor: colors,
          borderColor: '#ffffff',
          borderWidth: 2,
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              padding: 15,
              usePointStyle: true,
              pointStyle: 'circle',
              font: {
                size: 12,
                family: "'Inter', system-ui, sans-serif"
              }
            }
          },
          tooltip: {
            backgroundColor: 'rgba(17, 24, 39, 0.9)',
            padding: 12,
            cornerRadius: 8,
            titleFont: {
              size: 13,
              weight: 600
            },
            bodyFont: {
              size: 12
            },
            callbacks: {
              label: (context) => {
                const label = context.label || '';
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value} (${percentage}%)`;
              }
            }
          }
        },
        animation: {
          animateRotate: true,
          animateScale: true,
          duration: 1000,
          easing: 'easeOutQuart'
        }
      }
    });
  }

  function updateChart() {
    if (!chart) return;

    const sortedData = [...data].sort((a, b) => b.count - a.count).slice(0, 8);
    
    chart.data.labels = sortedData.map(d => d.fachgebiet_name);
    chart.data.datasets[0].data = sortedData.map(d => d.count);
    chart.update('active');
  }

  $effect(() => {
    if (data.length > 0) {
      if (chart) {
        updateChart();
      } else {
        createChart();
      }
    }
  });

  onMount(() => {
    createChart();
  });

  onDestroy(() => {
    if (chart) {
      chart.destroy();
      chart = null;
    }
  });
</script>

<div class="rounded-xl border border-gray-200 shadow-sm p-6">
  <div class="flex items-center justify-between mb-4">
    <h3 class="text-lg font-semibold text-gray-900">Verteilung nach Fachgebiet</h3>
    <span class="text-sm text-gray-500">Top {Math.min(data.length, 8)} Fachgebiete</span>
  </div>
  <div class="relative h-64">
    <canvas bind:this={canvas}></canvas>
  </div>
</div>
