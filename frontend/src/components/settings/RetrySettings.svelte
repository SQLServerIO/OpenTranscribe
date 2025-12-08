<script lang="ts">
  import { onMount } from 'svelte';
  import { AdminSettingsApi, type RetryConfig } from '../../lib/api/adminSettings';
  import { toastStore } from '../../stores/toast';

  // State
  let loading = true;
  let saving = false;
  let retryConfig: RetryConfig | null = null;

  // Form state
  let maxRetries = 3;
  let retryLimitEnabled = true;
  let hasChanges = false;

  // Track original values for change detection
  let originalMaxRetries = 3;
  let originalRetryLimitEnabled = true;

  onMount(async () => {
    await loadConfig();
  });

  async function loadConfig() {
    loading = true;
    try {
      retryConfig = await AdminSettingsApi.getRetryConfig();
      maxRetries = retryConfig.max_retries;
      retryLimitEnabled = retryConfig.retry_limit_enabled;
      originalMaxRetries = maxRetries;
      originalRetryLimitEnabled = retryLimitEnabled;
      hasChanges = false;
    } catch (err: any) {
      console.error('Error loading retry config:', err);
      toastStore.error('Failed to load retry configuration');
    } finally {
      loading = false;
    }
  }

  function checkForChanges() {
    hasChanges = maxRetries !== originalMaxRetries || retryLimitEnabled !== originalRetryLimitEnabled;
  }

  $: {
    // Reactive change detection
    maxRetries;
    retryLimitEnabled;
    checkForChanges();
  }

  async function saveConfig() {
    saving = true;
    try {
      retryConfig = await AdminSettingsApi.updateRetryConfig({
        max_retries: maxRetries,
        retry_limit_enabled: retryLimitEnabled
      });
      originalMaxRetries = retryConfig.max_retries;
      originalRetryLimitEnabled = retryConfig.retry_limit_enabled;
      hasChanges = false;
      toastStore.success('Retry configuration saved successfully');
    } catch (err: any) {
      console.error('Error saving retry config:', err);
      const errorMsg = err.response?.data?.detail || 'Failed to save retry configuration';
      toastStore.error(errorMsg);
    } finally {
      saving = false;
    }
  }

  function resetToDefaults() {
    maxRetries = 3;
    retryLimitEnabled = true;
  }
</script>

<div class="retry-settings">
  <h3 class="section-title">Retry Configuration</h3>
  <p class="section-description">
    Configure how many times files can be reprocessed before requiring admin intervention.
  </p>

  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <span>Loading configuration...</span>
    </div>
  {:else}
    <div class="settings-form">
      <!-- Enable/Disable Toggle -->
      <div class="form-group">
        <label class="toggle-label">
          <input
            type="checkbox"
            bind:checked={retryLimitEnabled}
            class="toggle-input"
          />
          <span class="toggle-switch"></span>
          <span class="toggle-text">Enable retry limits</span>
        </label>
        <p class="help-text">
          When disabled, files can be reprocessed unlimited times without admin intervention.
        </p>
      </div>

      <!-- Max Retries Input (only shown when enabled) -->
      {#if retryLimitEnabled}
        <div class="form-group">
          <label for="maxRetries" class="form-label">Maximum retry attempts</label>
          <div class="input-with-hint">
            <input
              type="number"
              id="maxRetries"
              bind:value={maxRetries}
              min="0"
              max="99"
              class="form-input number-input"
            />
            <span class="input-hint">0 = unlimited</span>
          </div>
          <p class="help-text">
            Number of times a file can be reprocessed before requiring an admin to reset the counter.
            Set to 0 for unlimited retries (same as disabling limits).
          </p>
        </div>
      {/if}

      <!-- Current Status -->
      <div class="status-box">
        <div class="status-icon">
          {#if retryLimitEnabled && maxRetries > 0}
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>
          {:else}
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>
            </svg>
          {/if}
        </div>
        <div class="status-text">
          {#if !retryLimitEnabled || maxRetries === 0}
            <strong>Retry limits disabled</strong> - Users can reprocess files unlimited times.
          {:else}
            <strong>Retry limits enabled</strong> - Users can reprocess files up to {maxRetries} time{maxRetries === 1 ? '' : 's'} before needing admin reset.
          {/if}
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="button-group">
        <button
          type="button"
          class="btn btn-secondary"
          on:click={resetToDefaults}
          disabled={saving}
        >
          Reset to Defaults
        </button>
        <button
          type="button"
          class="btn btn-primary"
          on:click={saveConfig}
          disabled={saving || !hasChanges}
        >
          {#if saving}
            <span class="spinner-small"></span>
            Saving...
          {:else}
            Save Changes
          {/if}
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  .retry-settings {
    padding: 0.5rem;
  }

  .section-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-color);
    margin: 0 0 0.5rem 0;
  }

  .section-description {
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin: 0 0 1.5rem 0;
  }

  .loading-state {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 2rem;
    color: var(--text-secondary);
  }

  .spinner {
    width: 24px;
    height: 24px;
    border: 2px solid var(--border-color);
    border-top-color: var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .spinner-small {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    display: inline-block;
    margin-right: 0.5rem;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .settings-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .form-label {
    font-weight: 500;
    color: var(--text-color);
    font-size: 0.875rem;
  }

  .toggle-label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    user-select: none;
  }

  .toggle-input {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-switch {
    position: relative;
    width: 44px;
    height: 24px;
    background-color: var(--border-color);
    border-radius: 12px;
    transition: background-color 0.2s ease;
    flex-shrink: 0;
  }

  .toggle-switch::after {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    background-color: white;
    border-radius: 50%;
    transition: transform 0.2s ease;
  }

  .toggle-input:checked + .toggle-switch {
    background-color: var(--primary-color);
  }

  .toggle-input:checked + .toggle-switch::after {
    transform: translateX(20px);
  }

  .toggle-text {
    font-weight: 500;
    color: var(--text-color);
  }

  .help-text {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    margin: 0;
    line-height: 1.4;
  }

  .input-with-hint {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .form-input {
    padding: 0.625rem 0.875rem;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    background-color: var(--background-color);
    color: var(--text-color);
    font-size: 0.875rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .form-input:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .number-input {
    width: 100px;
  }

  .input-hint {
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .status-box {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 1rem;
    background-color: var(--background-color);
    border: 1px solid var(--border-color);
    border-radius: 8px;
  }

  .status-icon {
    color: var(--text-secondary);
    flex-shrink: 0;
    margin-top: 2px;
  }

  .status-text {
    font-size: 0.875rem;
    color: var(--text-color);
    line-height: 1.5;
  }

  .status-text strong {
    display: block;
    margin-bottom: 0.25rem;
  }

  .button-group {
    display: flex;
    gap: 0.75rem;
    justify-content: flex-end;
    padding-top: 0.5rem;
    border-top: 1px solid var(--border-color);
    margin-top: 0.5rem;
  }

  .btn {
    padding: 0.625rem 1.25rem;
    border-radius: 6px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    border: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-primary {
    background-color: var(--primary-color);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background-color: var(--primary-hover);
  }

  .btn-secondary {
    background-color: var(--surface-color);
    color: var(--text-color);
    border: 1px solid var(--border-color);
  }

  .btn-secondary:hover:not(:disabled) {
    background-color: var(--background-color);
  }
</style>
