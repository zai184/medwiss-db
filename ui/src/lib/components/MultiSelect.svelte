<script lang="ts">
  import { tick } from 'svelte';
  import { slide } from 'svelte/transition';

  type Option = { id: string | number; label: string };

  let {
    options = [],
    selected = $bindable<(string | number)[]>([]),
    label = '',
    placeholder = 'Wählen Sie...',
    searchPlaceholder = 'Suchen...',
    allowCreate = false,
    createLabel = '+ Neu erstellen',
    disabled = false,
    onchange,
    oncreate
  }: {
    options?: Option[];
    selected?: (string | number)[];
    label?: string;
    placeholder?: string;
    searchPlaceholder?: string;
    allowCreate?: boolean;
    createLabel?: string;
    disabled?: boolean;
    onchange?: (detail: { selected: (string | number)[] }) => void;
    oncreate?: (detail: { value: string }) => void;
  } = $props();

  let isOpen = $state(false);
  let searchQuery = $state('');
  let dropdownElement: HTMLDivElement | undefined = $state();
  let searchInput: HTMLInputElement | undefined = $state();

  const filteredOptions = $derived(
    options.filter(
      (option) =>
        option.label.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !selected.includes(option.id)
    )
  );

  const selectedOptions = $derived(options.filter((option) => selected.includes(option.id)));

  const canCreate = $derived(
    allowCreate &&
      searchQuery.trim() !== '' &&
      !options.some((o) => o.label.toLowerCase() === searchQuery.toLowerCase())
  );

  function notifyChange() {
    onchange?.({ selected });
  }

  function toggleDropdown() {
    if (disabled) return;
    isOpen = !isOpen;
    if (isOpen) {
      tick().then(() => searchInput?.focus());
    }
  }

  function closeDropdown() {
    isOpen = false;
    searchQuery = '';
  }

  function toggleOption(id: string | number) {
    if (selected.includes(id)) {
      selected = selected.filter((s) => s !== id);
    } else {
      selected = [...selected, id];
    }
    notifyChange();
  }

  function removeOption(id: string | number) {
    selected = selected.filter((s) => s !== id);
    notifyChange();
  }

  function handleCreate() {
    if (canCreate) {
      oncreate?.({ value: searchQuery.trim() });
      searchQuery = '';
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      closeDropdown();
    } else if (e.key === 'Enter' && canCreate) {
      e.preventDefault();
      handleCreate();
    }
  }

  function handleClickOutside(e: MouseEvent) {
    if (dropdownElement && !dropdownElement.contains(e.target as Node)) {
      closeDropdown();
    }
  }
  const listboxId = $props.id();
</script>

<svelte:window onclick={handleClickOutside} />

<div class="multi-select" bind:this={dropdownElement} class:multi-select--disabled={disabled}>
  {#if label}
    <span class="multi-select__label">{label}</span>
  {/if}

  <div
    class="multi-select__trigger"
    class:multi-select__trigger--open={isOpen}
    onclick={toggleDropdown}
    onkeydown={(e) => e.key === 'Enter' && toggleDropdown()}
    role="combobox"
    aria-expanded={isOpen}
    aria-controls={listboxId}
    aria-haspopup="listbox"
    tabindex="0"
  >
    {#if selectedOptions.length === 0}
      <span class="multi-select__placeholder">{placeholder}</span>
    {:else}
      <div class="multi-select__tags">
        {#each selectedOptions as option (option.id)}
          <span class="multi-select__tag">
            {option.label}
            <button
              type="button"
              class="multi-select__tag-remove"
              onclick={(e) => {
                e.stopPropagation();
                removeOption(option.id);
              }}
              aria-label="{option.label} entfernen"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </span>
        {/each}
      </div>
    {/if}

    <svg
      class="multi-select__arrow"
      class:multi-select__arrow--open={isOpen}
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <polyline points="6 9 12 15 18 9"/>
    </svg>
  </div>

  {#if isOpen}
    <div class="multi-select__dropdown" transition:slide={{ duration: 150 }} role="listbox" id={listboxId}>
      <div class="multi-select__search">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        <input
          type="text"
          class="multi-select__search-input"
          placeholder={searchPlaceholder}
          bind:value={searchQuery}
          bind:this={searchInput}
          onkeydown={handleKeydown}
        />
      </div>

      <div class="multi-select__options">
        {#if filteredOptions.length === 0 && !canCreate}
          <div class="multi-select__empty">
            {searchQuery ? 'Keine Ergebnisse gefunden' : 'Keine Optionen verfügbar'}
          </div>
        {:else}
          {#each filteredOptions as option (option.id)}
            <button
              type="button"
              class="multi-select__option"
              class:multi-select__option--selected={selected.includes(option.id)}
              onclick={() => toggleOption(option.id)}
              role="option"
              aria-selected={selected.includes(option.id)}
            >
              <span class="multi-select__option-checkbox">
                {#if selected.includes(option.id)}
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                {/if}
              </span>
              <span class="multi-select__option-label">{option.label}</span>
            </button>
          {/each}

          {#if canCreate}
            <button type="button" class="multi-select__create" onclick={handleCreate}>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              {createLabel} "{searchQuery}"
            </button>
          {/if}
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .multi-select {
    position: relative;
    width: 100%;
  }

  .multi-select--disabled {
    opacity: 0.6;
    pointer-events: none;
  }

  .multi-select__label {
    display: block;
    font-size: var(--font-size-sm, 0.875rem);
    font-weight: 500;
    color: var(--color-text-secondary, #6b7280);
    margin-bottom: 0.5rem;
  }

  .multi-select__trigger {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 44px;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--color-border, #e5e7eb);
    border-radius: var(--radius-md, 0.5rem);
    background: var(--color-background-primary, #fff);
    cursor: pointer;
    gap: 0.5rem;
  }

  .multi-select__trigger--open {
    border-color: var(--color-primary, #2563eb);
    box-shadow: var(--shadow-focus, 0 0 0 3px rgba(37, 99, 235, 0.15));
  }

  .multi-select__placeholder {
    color: var(--color-text-tertiary, #9ca3af);
    font-size: var(--font-size-sm, 0.875rem);
  }

  .multi-select__tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
    flex: 1;
  }

  .multi-select__tag {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.125rem 0.5rem;
    background: var(--color-primary-subtle, #eff6ff);
    color: var(--color-primary, #2563eb);
    border-radius: var(--radius-sm, 0.25rem);
    font-size: var(--font-size-xs, 0.75rem);
  }

  .multi-select__tag-remove {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: none;
    background: none;
    color: inherit;
    cursor: pointer;
    opacity: 0.7;
  }

  .multi-select__tag-remove:hover {
    opacity: 1;
  }

  .multi-select__arrow {
    flex-shrink: 0;
    transition: transform 0.15s ease;
    color: var(--color-text-secondary, #6b7280);
  }

  .multi-select__arrow--open {
    transform: rotate(180deg);
  }

  .multi-select__dropdown {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    z-index: 50;
    background: var(--color-background-primary, #fff);
    border: 1px solid var(--color-border, #e5e7eb);
    border-radius: var(--radius-md, 0.5rem);
    box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1));
    overflow: hidden;
  }

  .multi-select__search {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--color-border, #e5e7eb);
    color: var(--color-text-secondary, #6b7280);
  }

  .multi-select__search-input {
    flex: 1;
    border: none;
    outline: none;
    font-size: var(--font-size-sm, 0.875rem);
    background: transparent;
    color: var(--color-text-primary, #111827);
  }

  .multi-select__options {
    max-height: 240px;
    overflow-y: auto;
  }

  .multi-select__empty {
    padding: 1rem;
    text-align: center;
    color: var(--color-text-secondary, #6b7280);
    font-size: var(--font-size-sm, 0.875rem);
  }

  .multi-select__option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.625rem 0.75rem;
    border: none;
    background: none;
    text-align: left;
    cursor: pointer;
    font-size: var(--font-size-sm, 0.875rem);
    color: var(--color-text-primary, #111827);
  }

  .multi-select__option:hover {
    background: var(--color-background-secondary, #f9fafb);
  }

  .multi-select__option--selected {
    background: var(--color-primary-subtle, #eff6ff);
  }

  .multi-select__option-checkbox {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1rem;
    height: 1rem;
    border: 1px solid var(--color-border, #d1d5db);
    border-radius: 0.25rem;
    flex-shrink: 0;
    color: var(--color-primary, #2563eb);
  }

  .multi-select__option--selected .multi-select__option-checkbox {
    border-color: var(--color-primary, #2563eb);
    background: var(--color-primary-subtle, #eff6ff);
  }

  .multi-select__create {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.625rem 0.75rem;
    border: none;
    border-top: 1px solid var(--color-border, #e5e7eb);
    background: var(--color-background-secondary, #f9fafb);
    text-align: left;
    cursor: pointer;
    font-size: var(--font-size-sm, 0.875rem);
    color: var(--color-primary, #2563eb);
    font-weight: 500;
  }

  .multi-select__create:hover {
    background: var(--color-primary-subtle, #eff6ff);
  }
</style>
