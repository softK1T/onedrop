export function formatMoney(amountMinor: number, currency: string): string {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(amountMinor / 100);
}

export function formatTime(iso: string): string {
  return new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' }).format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso));
}

export function entityLabel(type: string): string {
  return ({ task: 'Task', event: 'Event', expense: 'Expense', meal: 'Meal', habit: 'Habit', habit_log: 'Habit check-in', note: 'Note' } as Record<string, string>)[type] ?? type;
}
