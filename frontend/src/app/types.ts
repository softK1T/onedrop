export interface Task {
  id: string;
  title: string;
  due_at: string | null;
  priority: string;
  status: string;
}

export interface EventRecord {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string | null;
}

export interface CreatedEntity {
  entity_type: string;
  entity_id: string;
}

export interface Operation {
  inbox_item_id: string;
  status: string;
  input_type: string;
  created: CreatedEntity[];
  clarification_question: string | null;
  error: string | null;
  transcript: string | null;
}

export interface Dashboard {
  day: string;
  timezone: string;
  tasks: { today: number; overdue: number; completed_today: number; open_total: number };
  task_items: Task[];
  events: EventRecord[];
  expenses_today_minor: number;
  base_currency: string;
  nutrition: { calories: number; protein: number; fat: number; carbohydrates: number; contains_estimates: boolean };
  budget_warning: boolean;
  ai: { plan: string; remaining: number };
}

export interface InboxItem {
  id: string;
  input_type: string;
  status: string;
  raw_text: string | null;
  transcript: string | null;
  clarification_question: string | null;
  error: string | null;
  created_at: string;
}

export interface UserProfile {
  first_name: string | null;
  username: string | null;
  locale: string;
  settings: {
    timezone: string;
    base_currency: string;
    monthly_budget_minor: number | null;
    reminders_enabled: boolean;
    allow_training: boolean;
  };
}
