<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import Chart from 'chart.js/auto';
  import type { DiagnoseResponse } from '$lib/api';
  
  interface DiagnoseCount {
    diagnose: DiagnoseResponse;
    count: number;
  }
  
  interface Props {
    data: DiagnoseCount[];
  }

  let { data }: Props = $props();
  
  let canvas: HTMLCanvasElement;
  let chart: Chart | null = null;

  function createChart() {
    if (!canvas || data.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Sort by count descending and take top 10
    const sortedData = [...data].sort((a, b) => b.count - a.count).slice(0, 10);

    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.8)');
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.2)');

    chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: sortedData.map(d => d.diagnose.name),
        datasets: [{
          label: 'Einträge',
          data: sortedData.map(d => d.count),
          backgroundColor: gradient,
          borderColor: '#3b82f6',
          borderWidth: 1,
          borderRadius: 4,
          borderSkipped: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: {
            display: false
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
                return `${context.parsed.x} Einträge`;
              }
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            },
            border: {
              display: false
            },
            ticks: {
              font: {
                size: 11
              },
              color: '#6b7280'
            }
          },
          y: {
            grid: {
              display: false
            },
            border: {
              display: false
            },
            ticks: {
              font: {
                size: 12,
                weight: 500
              },
              color: '#374151'
            }
          }
        },
        animation: {
          duration: 1000,
          easing: 'easeOutQuart'
        }
      }
    });
  }

  function updateChart() {
    if (!chart) return;

    const sortedData = [...data].sort((a, b) => b.count - a.count).slice(0, 10);
    
    chart.data.labels = sortedData.map(d => d.diagnose.name);
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

<div class="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
  <div class="flex items-center justify-between mb-4">
    <h3 class="text-lg font-semibold text-gray-900">Top Diagnosen</h3>
    <span class="text-sm text-gray-500">Top {Math.min(data.length, 10)} Diagnosen</span>
  </div>
  <div class="relative h-80">
    <canvas bind:this={canvas}></canvas>
  </div>
</div>
