<script lang="ts">
  import {onMount} from 'svelte';
  import {Search, Plus, Activity, FileText} from 'lucide-svelte';
  import ActivityList from '$lib/components/ActivityList.svelte';
  import FachDistribution from '$lib/components/charts/FachDistribution.svelte';
  import DiagnoseBarChart from '$lib/components/charts/DiagnoseBarChart.svelte';
import {statsApi, entriesApi, filesApi, sourcesApi, type StatsOverview, type FachStats, type DiagnoseStats, type SyncResult, type SourceInfo, type DiagnoseResponse} from '$lib/api';

  const leitlinienDisabled = import.meta.env.VITE_DISABLE_LEITLINIEN === '1';
  let stats = $state<StatsOverview | null>(null);
  let fachStats = $state<FachStats[]>([]);
  let sources = $state<SourceInfo[]>([]);
  let diagnoseData = $state<{ diagnose: DiagnoseResponse; count: number }[]>([]);
  let loading = $state(true);
  let syncing = $state(false);
  let syncResult = $state<SyncResult | null>(null);
  let error = $state<string | null>(null);

  // Build category labels from source config
  const categoryLabels: Record<string, string> = $derived.by(() => {
    const labels: Record<string, string> = {};
    for (const src of sources) {
      labels[src.category] = src.display_name;
    }
    return labels;
  });

  // Fallback color map for distribution widgets (used before API loads)
  const dokumenttypColors: Record<string, string> = {
    'SOP': '#10B981',
    'Leitlinie': '#3B82F6',
    'Studie': '#8B5CF6',
    'Red Flags': '#EF4444',
    'Fragebogen': '#F59E0B',
    'Nachschlagen': '#6366F1',
    'Infoblatt': '#F97316',
    'Fachgebiet': '#84CC16',
    'Fall': '#F59E0B',
    'Pharma': '#EC4899',
    'Fortbildung': '#14B8A6',
    'Prüfung': '#A855F7',
    'Unkategorisiert': '#6B7280'
  };

  const fallbackCategoryColors: Record<string, string> = {
    ...dokumenttypColors,
    'sop': '#3b82f6',
    'leitlinien': '#10b981',
    'studien': '#8b5cf6',
    'faelle': '#f59e0b',
    'red_flags': '#ef4444',
    'frageboegen': '#06b6d4',
    'nachschlagen': '#6366f1',
    'infoblaetter': '#f97316',
    'faecher': '#84cc16',
    'pharma': '#ec4899',
    'fortbildung': '#14b8a6',
    'forschung': '#8b5cf6'
  };

  // Dynamic category colors from API sources (with fallback)
  const categoryColors: Record<string, string> = $derived.by(() => {
    const colors: Record<string, string> = { ...fallbackCategoryColors };
    for (const src of sources) {
      if (!colors[src.category]) {
        colors[src.category] = '#6b7280';
      }
    }
    return colors;
  });

  const categoryStats = $derived(
    Object.entries(stats?.entries_by_category || {})
      .map(([name, count]) => ({
        name: categoryLabels[name] || name,
        key: name,
        count,
        color: dokumenttypColors[name] || categoryColors[name] || '#6b7280'
      }))
      .sort((a, b) => b.count - a.count)
  );

  function calculatePercentage(value: number, total: number): string {
    if (total === 0) return '0%';
    return Math.round((value / total) * 100) + '%';
  }

  async function loadDashboardData() {
    try {
      loading = true;
      error = null;

      // Load all data in parallel
      const [overview, byFach, byDiagnose, sourcesData] = await Promise.all([
        statsApi.getOverview(),
        statsApi.getByFach(),
        statsApi.getByDiagnose(),
        sourcesApi.getAll()
      ]);

      stats = overview;
      fachStats = byFach;
      diagnoseData = byDiagnose.map((d: DiagnoseStats) => ({
        diagnose: {
          id: d.diagnose_id,
          code: d.diagnose_code,
          name: d.diagnose_name,
          beschreibung: null
        },
        count: d.count
      }));
      sources = sourcesData;
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
      error = 'Fehler beim Laden der Dashboard-Daten';
    } finally {
      loading = false;
    }
  }

  async function syncAndRefresh() {
    try {
      syncing = true;
      syncResult = null;
      error = null;

      // Trigger file sync
      const result = await filesApi.triggerSync();
      syncResult = result;

      // Reload dashboard data to reflect new entries
      await loadDashboardData();
    } catch (err: any) {
      console.error('Sync failed:', err);
      error = err.response?.data?.detail || 'Fehler bei der Dateisynchronisation';
    } finally {
      syncing = false;
    }
  }

  onMount(() => {
    loadDashboardData();

    // Poll sync status every 10 s; refetch lists when the index changed.
    let lastChange: string | null = null;
    const poll = setInterval(async () => {
      try {
        const status = await filesApi.getSyncStatus();
        if (lastChange !== null && status.last_change !== lastChange) {
          await loadDashboardData();
        }
        lastChange = status.last_change;
      } catch {
        // Sync endpoint unavailable — ignore, retry on next tick.
      }
    }, 10_000);

    return () => clearInterval(poll);
  });
</script>

<svelte:head>
  <title>Dashboard | MedWiss DB</title>
</svelte:head>

<div class="dashboard-page">
  {#if error}
  <div class="error-banner">
    <span>{error}</span>
    <button onclick={loadDashboardData} class="retry-btn">
      Erneut versuchen
    </button>
  </div>
  {/if}

  {#if syncResult}
  <div class="sync-result" class:sync-success={syncResult.success} class:sync-error={!syncResult.success}>
    <span class="sync-message">{syncResult.message}</span>
    {#if syncResult.changes_detected && (syncResult.changes_detected.imported > 0 || syncResult.changes_detected.updated
    > 0 || syncResult.changes_detected.deleted_entries > 0)}
    <span class="sync-details">
      {syncResult.changes_detected.imported} importiert,
      {syncResult.changes_detected.updated} aktualisiert,
      {syncResult.changes_detected.deleted_entries} gelöscht
    </span>
    {/if}
  </div>
  {/if}

  <section class="quick-actions">
    <h2 class="section-title">Schnellzugriff</h2>
    <div class="actions-grid">
      <a href="/eingabe" class="action-card primary">
        <div class="action-icon">
          <Plus size={20} />
        </div>
        <div class="action-content">
          <span class="action-label">Neuer Eintrag</span>
          <span class="action-description">Wissen hinzufügen</span>
        </div>
      </a>

      <a href="/search" class="action-card">
        <div class="action-icon emerald">
          <Search size={20} />
        </div>
        <div class="action-content">
          <span class="action-label">Suchen</span>
          <span class="action-description">Wissen finden</span>
        </div>
      </a>

      {#if !leitlinienDisabled}
      <a href="/leitlinien" class="action-card">
        <div class="action-icon emerald">
          <FileText size={20} />
        </div>
        <div class="action-content">
          <span class="action-label">Leitlinien</span>
          <span class="action-description">AWMF-Richtlinien suchen</span>
        </div>
      </a>
      {/if}

      <button onclick={syncAndRefresh} disabled={syncing} class="action-card">
        <div class="action-icon amber">
          <Activity size={20} />
        </div>
        <div class="action-content">
          <span class="action-label">{syncing ? 'Synchronisiere...' : 'Synchronisieren'}</span>
        </div>
      </button>
    </div>
  </section>

  <section class="stats-section">
    <h2 class="section-title">Übersicht</h2>
    <div class="stats-list">
      <div class="stat-row">
        <span class="stat-label">Einträge gesamt</span>
        <span class="stat-value">
          {stats?.total_entries || 0}
          {#if stats && stats.total_entries > 0}
            <span class="stat-trend positive">+12%</span>
          {/if}
        </span>
      </div>

      {#each categoryStats.slice(0, 2) as cat}
        <div class="stat-row">
          <span class="stat-label">{cat.name}</span>
          <span class="stat-value">{cat.count}</span>
        </div>
      {/each}
    </div>
  </section>

  <section class="charts-section">
    <h2 class="section-title">Verteilung</h2>
    <div class="charts-grid">
      <div class="chart-card">
        <h3 class="chart-title">Nach Fachgebiet</h3>
        <div class="chart-content">
          <FachDistribution data={fachStats} />
        </div>
      </div>

      <div class="chart-card">
        <h3 class="chart-title">Häufigste Diagnosen</h3>
        <div class="chart-content">
          <DiagnoseBarChart data={diagnoseData} />
        </div>
      </div>
    </div>
  </section>

  <section class="distribution-section">
    <h2 class="section-title">Verteilung</h2>
    <div class="distribution-grid">
      <div class="distribution-card">
        <h3>Kategorien</h3>
        <div class="distribution-list">
          {#each categoryStats as cat}
            <div class="distribution-item">
              <div class="distribution-bar-wrapper">
                <div class="distribution-info">
                  <span class="distribution-name">{cat.name}</span>
                  <span class="distribution-count">{cat.count}</span>
                </div>
                <div class="distribution-bar-bg">
                  <div
                    class="distribution-bar"
                    style="width: {calculatePercentage(cat.count, stats?.total_entries || 1)}; background: {cat.color}"
                  ></div>
                </div>
              </div>
              <span class="distribution-percent">{calculatePercentage(cat.count, stats?.total_entries || 1)}</span>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </section>

  <section class="activity-section">
    <h2 class="section-title">Aktuelle Aktivität</h2>
    <div class="activity-card">
      <ActivityList entries={stats?.recent_entries || []} />
    </div>
  </section>
</div>

<style>
  .dashboard-page {
    max-width: 1000px;
    margin: 0 auto;
    padding: var(--space-6) var(--space-4);
  }

  /* Error Banner */
  .error-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4);
    background: var(--color-error-subtle);
    border: 1px solid var(--color-error);
    border-radius: var(--radius-lg);
    color: var(--color-error);
    margin-bottom: var(--space-6);
  }

  .retry-btn {
    padding: var(--space-2) var(--space-4);
    background: transparent;
    border: 1px solid var(--color-error);
    border-radius: var(--radius-md);
    color: var(--color-error);
    font-size: var(--font-size-sm);
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .retry-btn:hover {
    background: var(--color-error);
    color: white;
  }

  /* Sync Result */
  .sync-result {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4);
    border-radius: var(--radius-lg);
    margin-bottom: var(--space-6);
    font-size: var(--font-size-sm);
  }

  .sync-result.sync-success {
    background: #d1fae5;
    border: 1px solid #059669;
    color: #065f46;
  }

  .sync-result.sync-error {
    background: #fef3c7;
    border: 1px solid #d97706;
    color: #92400e;
  }

  .sync-message {
    font-weight: var(--font-weight-medium);
  }

  .sync-details {
    opacity: 0.8;
  }

  /* Section Titles */
  .section-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    margin-bottom: var(--space-4);
  }

  section {
    margin-bottom: var(--space-8);
  }

  /* Quick Actions */
  .actions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--space-3);
  }

  .action-card {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    text-decoration: none;
    transition: all var(--transition-fast);
    cursor: pointer;
  }

  .action-card:hover {
    border-color: var(--color-primary);
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
  }

  .action-card.primary {
    border-color: var(--color-primary);
    background: linear-gradient(135deg, var(--color-primary-subtle) 0%, var(--color-background-primary) 100%);
  }

  .action-card.primary:hover {
    background: var(--color-primary);
  }

  .action-card.primary:hover .action-icon,
  .action-card.primary:hover .action-label,
  .action-card.primary:hover .action-description {
    color: white;
  }

  .action-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    background: var(--color-background-tertiary);
    border-radius: var(--radius-md);
    color: var(--color-primary);
    flex-shrink: 0;
    transition: all var(--transition-fast);
  }

  .action-icon.emerald {
    color: #10b981;
    background: #d1fae5;
  }

  .action-icon.amber {
    color: #f59e0b;
    background: #fef3c7;
  }

  .action-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .action-label {
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    font-size: var(--font-size-sm);
  }

  .action-description {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
  }

  /* Overview Stats - plain list */
  .stats-list {
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    overflow: hidden;
  }

  .stat-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-5);
  }

  .stat-row + .stat-row {
    border-top: 1px solid var(--color-border);
  }

  .stat-label {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
  }

  .stat-value {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
  }

  .stat-trend {
    padding: 2px var(--space-2);
    border-radius: var(--radius-full);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-medium);
  }

  .stat-trend.positive {
    background: #d1fae5;
    color: #059669;
  }

  /* Charts Section */
  .charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: var(--space-6);
  }

  .chart-card {
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl);
    padding: var(--space-6);
  }

  .chart-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    margin-bottom: var(--space-4);
  }

  .chart-content {
    min-height: 300px;
  }

  /* Distribution Section */
  .distribution-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: var(--space-6);
  }

  .distribution-card {
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl);
    padding: var(--space-6);
  }

  .distribution-card h3 {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    margin-bottom: var(--space-5);
  }

  .distribution-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .distribution-item {
    display: flex;
    align-items: center;
    gap: var(--space-4);
  }

  .distribution-bar-wrapper {
    flex: 1;
  }

  .distribution-info {
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--space-1);
  }

  .distribution-name {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  .distribution-count {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-primary);
  }

  .distribution-bar-bg {
    height: 8px;
    background: var(--color-background-tertiary);
    border-radius: var(--radius-full);
    overflow: hidden;
  }

  .distribution-bar {
    height: 100%;
    border-radius: var(--radius-full);
    transition: width 0.5s ease;
  }

  .distribution-percent {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-tertiary);
    min-width: 40px;
    text-align: right;
  }

  /* Activity Section */
  .activity-card {
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl);
    padding: var(--space-6);
    max-width: 800px;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .dashboard-page {
      padding: var(--space-4);
    }
    .actions-grid {
      grid-template-columns: 1fr;
    }

    .charts-grid,
    .distribution-grid {
      grid-template-columns: 1fr;
    }

    .action-card {
      padding: var(--space-4);
    }
  }
</style>
