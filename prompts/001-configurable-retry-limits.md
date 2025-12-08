# Prompt 001: Configurable Retry Limits with Reset UI

## Objective
Implement a comprehensive retry management system that allows:
1. Admin UI button to reset retry count for individual files
2. Configurable maximum retry count (system-wide setting)
3. Option to disable retry limits entirely

## Context

### Current State
- Retry count tracked per file in `media_file` table (`retry_count`, `max_retries` columns)
- Default max_retries: 3 (hardcoded in model)
- Reprocess endpoint blocks at limit with HTTP 400: "File has reached maximum retry attempts"
- Admins can bypass limits but require database access or script to reset
- Workaround script: `./scripts/reset-retries.sh`

### Problem
Users hit max retry limit and get "400 Bad Request" when trying to reprocess files. Currently requires database access or admin script to fix. Need admin UI to reset and configure retry behavior.

## Implementation Plan

### Phase 1: Backend System Settings

#### 1.1 Add System Settings Model
Create or update system settings to include retry configuration.

**File:** `backend/app/models/settings.py` (create if needed)
```python
class SystemSettings(Base):
    """System-wide settings stored in database"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

**Settings Keys:**
- `transcription.max_retries`: Integer, default 3 (0 = unlimited)
- `transcription.retry_limit_enabled`: Boolean, default true

#### 1.2 System Settings Service
**File:** `backend/app/services/system_settings.py`
```python
def get_setting(db: Session, key: str, default: Any = None) -> Any:
    """Get a system setting by key"""

def set_setting(db: Session, key: str, value: Any, description: str = None) -> None:
    """Set a system setting"""

def get_retry_config(db: Session) -> dict:
    """Get retry configuration as structured dict"""
    return {
        "max_retries": int(get_setting(db, "transcription.max_retries", 3)),
        "retry_limit_enabled": get_setting(db, "transcription.retry_limit_enabled", "true") == "true"
    }
```

#### 1.3 Update Database Init
**File:** `database/init_db.sql`
Add `system_settings` table and seed default values.

### Phase 2: Backend API Endpoints

#### 2.1 Reset Retry Endpoint (Admin)
**File:** `backend/app/api/endpoints/files/management.py`

Add endpoint: `POST /api/files/{file_uuid}/reset-retries`
- Requires admin role
- Resets `retry_count` to 0
- Returns updated file status

```python
@router.post("/{file_uuid}/reset-retries")
async def reset_file_retry_count(
    file_uuid: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
) -> FileStatusDetail:
    """Reset retry count for a file (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    media_file = get_media_file_by_uuid(db, file_uuid)
    if not media_file:
        raise HTTPException(status_code=404, detail="File not found")

    media_file.retry_count = 0
    db.commit()

    return get_file_status_detail(db, media_file)
```

#### 2.2 System Settings Endpoints
**File:** `backend/app/api/endpoints/admin/settings.py` (create)

```python
@router.get("/retry-config")
async def get_retry_configuration(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_superuser),
) -> dict:
    """Get retry configuration"""

@router.put("/retry-config")
async def update_retry_configuration(
    config: RetryConfigUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_superuser),
) -> dict:
    """Update retry configuration"""
```

#### 2.3 Update Retry Limit Check
**File:** `backend/app/api/endpoints/files/reprocess.py` (lines 148-152)

Replace hardcoded check with dynamic config:
```python
from app.services.system_settings import get_retry_config

retry_config = get_retry_config(db)
if not is_admin and retry_config["retry_limit_enabled"]:
    if media_file.retry_count >= retry_config["max_retries"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File has reached maximum retry attempts ({retry_config['max_retries']}). Contact admin for help.",
        )
```

Also update in:
- `backend/app/api/endpoints/files/management.py` (line 227)

### Phase 3: Frontend Components

#### 3.1 Reset Retry Button
**File:** `frontend/src/components/FileActions.svelte` (or appropriate location)

Add conditional "Reset Retries" button for admins when file is at retry limit:
```svelte
{#if isAdmin && file.retry_count >= file.max_retries}
  <button
    class="btn btn-warning btn-sm"
    on:click={handleResetRetries}
    disabled={resettingRetries}
  >
    {resettingRetries ? 'Resetting...' : 'Reset Retries'}
  </button>
{/if}
```

#### 3.2 Retry Settings Panel
**File:** `frontend/src/components/settings/RetrySettings.svelte` (create)

Admin-only settings panel in System Settings section:
```svelte
<script lang="ts">
  export let retryConfig = {
    max_retries: 3,
    retry_limit_enabled: true
  };

  let maxRetries = retryConfig.max_retries;
  let limitEnabled = retryConfig.retry_limit_enabled;

  async function saveConfig() {
    // POST to /api/admin/settings/retry-config
  }
</script>

<div class="settings-section">
  <h3>Retry Configuration</h3>

  <div class="form-group">
    <label class="toggle">
      <input type="checkbox" bind:checked={limitEnabled} />
      <span>Enable retry limits</span>
    </label>
    <p class="help-text">When disabled, files can be retried unlimited times</p>
  </div>

  {#if limitEnabled}
    <div class="form-group">
      <label for="maxRetries">Maximum retry attempts</label>
      <input
        type="number"
        id="maxRetries"
        bind:value={maxRetries}
        min="1"
        max="99"
      />
      <p class="help-text">Number of times a file can be reprocessed before requiring admin reset</p>
    </div>
  {/if}

  <button class="btn btn-primary" on:click={saveConfig}>
    Save Changes
  </button>
</div>
```

#### 3.3 Update Settings Modal
**File:** `frontend/src/components/SettingsModal.svelte`

Add "Retry Settings" to admin section sidebar:
```typescript
{
  title: 'Administration',
  items: [
    // ... existing items
    { id: 'admin-retry-settings' as SettingsSection, label: 'Retry Settings', icon: 'refresh' }
  ]
}
```

#### 3.4 API Client Updates
**File:** `frontend/src/lib/api/admin.ts` (create or update)

```typescript
export async function getRetryConfig(): Promise<RetryConfig> {
  const response = await axiosInstance.get('/admin/settings/retry-config');
  return response.data;
}

export async function updateRetryConfig(config: RetryConfigUpdate): Promise<RetryConfig> {
  const response = await axiosInstance.put('/admin/settings/retry-config', config);
  return response.data;
}

export async function resetFileRetries(fileUuid: string): Promise<FileStatusDetail> {
  const response = await axiosInstance.post(`/files/${fileUuid}/reset-retries`);
  return response.data;
}
```

### Phase 4: Schema Updates

#### 4.1 Backend Schemas
**File:** `backend/app/schemas/admin.py` (create or update)

```python
class RetryConfig(BaseModel):
    max_retries: int
    retry_limit_enabled: bool

class RetryConfigUpdate(BaseModel):
    max_retries: Optional[int] = None
    retry_limit_enabled: Optional[bool] = None

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, v):
        if v is not None and (v < 1 or v > 99):
            raise ValueError("max_retries must be between 1 and 99")
        return v
```

#### 4.2 Frontend Types
**File:** `frontend/src/lib/types/admin.ts` (create or update)

```typescript
export interface RetryConfig {
  max_retries: number;
  retry_limit_enabled: boolean;
}

export interface RetryConfigUpdate {
  max_retries?: number;
  retry_limit_enabled?: boolean;
}
```

## Files to Modify

### Backend
1. `backend/app/models/settings.py` - Create SystemSettings model
2. `backend/app/services/system_settings.py` - Create settings service
3. `backend/app/api/endpoints/admin/settings.py` - Create admin settings endpoints
4. `backend/app/api/endpoints/files/management.py` - Add reset-retries endpoint
5. `backend/app/api/endpoints/files/reprocess.py` - Use dynamic retry config (lines 148-152)
6. `backend/app/schemas/admin.py` - Add retry config schemas
7. `backend/app/api/router.py` - Register admin settings router
8. `database/init_db.sql` - Add system_settings table

### Frontend
1. `frontend/src/components/settings/RetrySettings.svelte` - Create settings panel
2. `frontend/src/components/SettingsModal.svelte` - Add to admin section
3. `frontend/src/lib/api/admin.ts` - Add API client methods
4. `frontend/src/lib/types/admin.ts` - Add TypeScript types
5. `frontend/src/components/FileActions.svelte` or similar - Add reset button

## Testing Checklist

- [ ] System settings table created and seeded
- [ ] Admin can view retry configuration in Settings
- [ ] Admin can change max retry count
- [ ] Admin can disable retry limits
- [ ] Retry limit check uses dynamic config
- [ ] Disabled limits allow unlimited retries
- [ ] Admin reset button appears when file at limit
- [ ] Reset button resets retry_count to 0
- [ ] Non-admins cannot access settings or reset
- [ ] Changes persist across restarts
- [ ] Frontend shows correct retry info

## Success Criteria

1. Admins can reset retry counts for individual files via UI button
2. Admins can configure maximum retry count (1-99) in settings
3. Admins can disable retry limits entirely (unlimited retries)
4. Configuration persists in database
5. Non-admin users see appropriate error messages
6. Existing functionality (reprocess with speaker settings) remains intact
