export interface Task {
  id: string;
  title: string;
  due_at: string | null;
  reminder_at: string | null;
  priority: string;
  status: string;
}

export interface EventRecord {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string | null;
  reminder_at: string | null;
}

export interface CreatedEntity { entity_type: string; entity_id: string }
export interface CaptureIntent { type: string; confidence: number; source_fragment: string; fields: Record<string, unknown> }
export interface CaptureResult { language: string; timezone: string; intents: CaptureIntent[]; needs_confirmation: boolean; clarification_question: string | null }
export interface Operation { inbox_item_id: string; status: string; input_type: string; created: CreatedEntity[]; clarification_question: string | null; error: string | null; transcript: string | null; ai_result: CaptureResult | null; processing_ms: number | null; created_at: string }
export interface Dashboard { day: string; timezone: string; tasks: { today: number; overdue: number; completed_today: number; open_total: number }; task_items: Task[]; events: EventRecord[]; expenses_today_minor: number; base_currency: string; nutrition: { calories: number; protein: number; fat: number; carbohydrates: number; contains_estimates: boolean }; budget_warning: boolean; ai: { plan: string; remaining: number } }
export interface InboxItem { id: string; input_type: string; status: string; raw_text: string | null; transcript: string | null; clarification_question: string | null; error: string | null; created_at: string }
export interface UserSettings { timezone: string; base_currency: string; monthly_budget_minor: number | null; reminders_enabled: boolean; task_reminders: boolean; event_reminders: boolean; habit_reminders: boolean; morning_digest: boolean; budget_warnings: boolean; morning_digest_hour: number; quiet_hours_start: number; quiet_hours_end: number; task_reminder_lead_minutes: number; event_reminder_lead_minutes: number; budget_warning_threshold_percent: number; allow_training: boolean }
export interface UserProfile { first_name: string | null; username: string | null; locale: string; is_admin: boolean; settings: UserSettings }
export interface AdminOverview { users_count: number; captures_by_status: Record<string, number>; failed_captures_count: number; pending_notifications_count: number; failed_notifications_count: number; ai_operations_count: number; ai_cost_micro: number; provider_cost_micro: Record<string, number>; active_subscriptions_count: number; payments_count: number; payment_stars_total: number }
