import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { UserProfile, UserSettings } from '@/app/types';
import { ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { settingsLabel } from '@/i18n/settings';
import { api } from '@/lib/api';

const CURRENCIES = ['PLN', 'EUR', 'USD', 'UAH'] as const;
const ME_KEY = ['me'];
const MAX_LEAD_MINUTES = 1440;

type SettingsPatch = Partial<UserSettings>;

function NumberField({
  label,
  value,
  min,
  max,
  disabled,
  onCommit,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  disabled?: boolean;
  onCommit: (next: number) => void;
}): JSX.Element {
  return (
    <label className="block">
      <span className="od-label">{label}</span>
      <input
        className="mt-1 w-full rounded-card border border-line bg-surface p-3"
        type="number"
        min={min}
        max={max}
        disabled={disabled}
        defaultValue={value}
        onBlur={(event) => {
          const next = Number(event.target.value);
          if (!Number.isFinite(next) || next < min || next > max || next === value) return;
          onCommit(Math.round(next));
        }}
      />
    </label>
  );
}

function ToggleField({
  label,
  checked,
  disabled,
  onToggle,
}: {
  label: string;
  checked: boolean;
  disabled?: boolean;
  onToggle: (next: boolean) => void;
}): JSX.Element {
  return (
    <label className="flex min-h-touch items-center justify-between gap-4">
      <span>{label}</span>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onToggle(event.target.checked)}
      />
    </label>
  );
}

export function SettingsScreen(): JSX.Element {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ME_KEY, queryFn: () => api.get<UserProfile>('/me') });
  const t = (key: string): string => settingsLabel(query.data?.locale, key);

  const mutation = useMutation({
    mutationFn: (patch: SettingsPatch) => api.patch<UserProfile>('/me/settings', patch),
    onMutate: async (patch: SettingsPatch) => {
      await client.cancelQueries({ queryKey: ME_KEY });
      const previous = client.getQueryData<UserProfile>(ME_KEY);
      if (previous) {
        client.setQueryData<UserProfile>(ME_KEY, {
          ...previous,
          settings: { ...previous.settings, ...patch },
        });
      }
      return { previous };
    },
    onError: (_error, _patch, context) => {
      if (context?.previous) client.setQueryData<UserProfile>(ME_KEY, context.previous);
    },
    onSettled: () => void client.invalidateQueries({ queryKey: ME_KEY }),
  });

  if (query.isLoading) {
    return (
      <section className="p-4">
        <div className="od-skeleton h-10" />
        <div className="od-skeleton mt-4 h-40" />
      </section>
    );
  }
  if (query.isError || !query.data) {
    return (
      <section className="p-4">
        <ErrorCard message={t('loadFailed')} retry={() => void query.refetch()} />
      </section>
    );
  }

  const settings = query.data.settings;
  const save = (patch: SettingsPatch): void => mutation.mutate(patch);
  const remindersOff = !settings.reminders_enabled;

  return (
    <section className="p-4">
      <ScreenHeader title={t('title')} />
      {mutation.isError && (
        <p className="mb-3 rounded-card bg-danger/15 p-3 text-sm text-danger" role="alert">
          {t('saveFailed')}
        </p>
      )}

      <div className="od-card space-y-4">
        <p className="od-label">{t('general')}</p>
        <label className="block">
          <span className="od-label">{t('timezone')}</span>
          <input
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            defaultValue={settings.timezone}
            onBlur={(event) => {
              const next = event.target.value.trim();
              if (next && next !== settings.timezone) save({ timezone: next });
            }}
          />
        </label>
        <label className="block">
          <span className="od-label">{t('currency')}</span>
          <select
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            value={settings.base_currency}
            onChange={(event) => save({ base_currency: event.target.value })}
          >
            {CURRENCIES.map((currency) => (
              <option key={currency}>{currency}</option>
            ))}
          </select>
        </label>
        <NumberField
          label={t('budget')}
          value={Math.round((settings.monthly_budget_minor ?? 0) / 100)}
          min={0}
          max={10_000_000}
          onCommit={(next) => save({ monthly_budget_minor: next * 100 })}
        />
      </div>

      <div className="od-card mt-4 space-y-4">
        <p className="od-label">{t('reminders')}</p>
        <ToggleField
          label={t('reminders')}
          checked={settings.reminders_enabled}
          onToggle={(next) => save({ reminders_enabled: next })}
        />
        <p className="text-xs text-ink-muted">{t('remindersHint')}</p>
        <ToggleField
          label={t('morningDigest')}
          checked={settings.morning_digest}
          disabled={remindersOff}
          onToggle={(next) => save({ morning_digest: next })}
        />
        <NumberField
          label={t('digestHour')}
          value={settings.morning_digest_hour}
          min={0}
          max={23}
          disabled={remindersOff}
          onCommit={(next) => save({ morning_digest_hour: next })}
        />
        <ToggleField
          label={t('taskReminders')}
          checked={settings.task_reminders}
          disabled={remindersOff}
          onToggle={(next) => save({ task_reminders: next })}
        />
        <NumberField
          label={t('taskLead')}
          value={settings.task_reminder_lead_minutes}
          min={0}
          max={MAX_LEAD_MINUTES}
          disabled={remindersOff}
          onCommit={(next) => save({ task_reminder_lead_minutes: next })}
        />
        <ToggleField
          label={t('eventReminders')}
          checked={settings.event_reminders}
          disabled={remindersOff}
          onToggle={(next) => save({ event_reminders: next })}
        />
        <NumberField
          label={t('eventLead')}
          value={settings.event_reminder_lead_minutes}
          min={0}
          max={MAX_LEAD_MINUTES}
          disabled={remindersOff}
          onCommit={(next) => save({ event_reminder_lead_minutes: next })}
        />
        <ToggleField
          label={t('habitReminders')}
          checked={settings.habit_reminders}
          disabled={remindersOff}
          onToggle={(next) => save({ habit_reminders: next })}
        />
      </div>

      <div className="od-card mt-4 space-y-4">
        <p className="od-label">{t('quietHours')}</p>
        <NumberField
          label={t('quietFrom')}
          value={settings.quiet_hours_start}
          min={0}
          max={23}
          disabled={remindersOff}
          onCommit={(next) => save({ quiet_hours_start: next })}
        />
        <NumberField
          label={t('quietTo')}
          value={settings.quiet_hours_end}
          min={0}
          max={23}
          disabled={remindersOff}
          onCommit={(next) => save({ quiet_hours_end: next })}
        />
        <p className="text-xs text-ink-muted">{t('quietHint')}</p>
      </div>

      <div className="od-card mt-4 space-y-4">
        <p className="od-label">{t('budgetWarnings')}</p>
        <ToggleField
          label={t('budgetWarnings')}
          checked={settings.budget_warnings}
          disabled={remindersOff}
          onToggle={(next) => save({ budget_warnings: next })}
        />
        <NumberField
          label={t('budgetThreshold')}
          value={settings.budget_warning_threshold_percent}
          min={1}
          max={100}
          disabled={remindersOff}
          onCommit={(next) => save({ budget_warning_threshold_percent: next })}
        />
      </div>
    </section>
  );
}
