import { DEFAULT_LOCALE, SUPPORTED_LOCALES, type Locale } from '@/i18n';

const en: Record<string, string> = {
  title: 'Today',
  tasks: 'Tasks',
  events: 'Events',
  habits: 'Habits',
  aiLeft: 'AI actions left',
  spent: 'Spent today',
  calories: 'Calories',
  budgetWarning: 'You are close to your monthly budget',
  empty: 'Nothing planned yet. Capture something below.',
  noHabits: 'No active habits.',
  done: 'Done',
  postpone: 'Tomorrow',
  noDue: 'no date, cannot postpone',
  edit: 'Rename',
  save: 'Save',
  cancel: 'Cancel',
  checkIn: 'Check in',
  checkedIn: 'Habit logged for today.',
  loadFailed: 'Could not load your dashboard.',
  saveFailed: 'That change was not saved and has been reverted.',
  retry: 'Try again',
};

const ru: Record<string, string> = {
  title: 'Сегодня',
  tasks: 'Задачи',
  events: 'События',
  habits: 'Привычки',
  aiLeft: 'Осталось AI-действий',
  spent: 'Потрачено сегодня',
  calories: 'Калории',
  budgetWarning: 'Вы близко к месячному бюджету',
  empty: 'На сегодня планов нет. Запишите что-нибудь.',
  noHabits: 'Активных привычек нет.',
  done: 'Готово',
  postpone: 'На завтра',
  noDue: 'без даты, перенос невозможен',
  edit: 'Переименовать',
  save: 'Сохранить',
  cancel: 'Отмена',
  checkIn: 'Отметить',
  checkedIn: 'Привычка отмечена на сегодня.',
  loadFailed: 'Не удалось загрузить сводку.',
  saveFailed: 'Изменение не сохранено и было отменено.',
  retry: 'Повторить',
};

const pl: Record<string, string> = {
  title: 'Dzisiaj',
  tasks: 'Zadania',
  events: 'Wydarzenia',
  habits: 'Nawyki',
  aiLeft: 'Pozostało akcji AI',
  spent: 'Wydano dzisiaj',
  calories: 'Kalorie',
  budgetWarning: 'Zbliżasz się do miesięcznego budżetu',
  empty: 'Nic nie zaplanowano. Zapisz coś poniżej.',
  noHabits: 'Brak aktywnych nawyków.',
  done: 'Gotowe',
  postpone: 'Na jutro',
  noDue: 'bez daty, nie można przenieść',
  edit: 'Zmień nazwę',
  save: 'Zapisz',
  cancel: 'Anuluj',
  checkIn: 'Odnotuj',
  checkedIn: 'Nawyk odnotowany na dzisiaj.',
  loadFailed: 'Nie udało się wczytać podsumowania.',
  saveFailed: 'Zmiana nie została zapisana i została cofnięta.',
  retry: 'Spróbuj ponownie',
};

const uk: Record<string, string> = {
  title: 'Сьогодні',
  tasks: 'Завдання',
  events: 'Події',
  habits: 'Звички',
  aiLeft: 'Залишилося AI-дій',
  spent: 'Витрачено сьогодні',
  calories: 'Калорії',
  budgetWarning: 'Ви близько до місячного бюджету',
  empty: 'На сьогодні планів немає. Запишіть що-небудь.',
  noHabits: 'Активних звичок немає.',
  done: 'Готово',
  postpone: 'На завтра',
  noDue: 'без дати, перенести неможливо',
  edit: 'Перейменувати',
  save: 'Зберегти',
  cancel: 'Скасувати',
  checkIn: 'Відмітити',
  checkedIn: 'Звичку відмічено на сьогодні.',
  loadFailed: 'Не вдалося завантажити зведення.',
  saveFailed: 'Зміна не збереглася і була скасована.',
  retry: 'Спробувати знову',
};

export const TODAY_MESSAGES: Record<Locale, Record<string, string>> = { en, ru, pl, uk };

export function todayLabel(locale: string | null | undefined, key: string): string {
  const short = (locale ?? DEFAULT_LOCALE).split('-')[0]?.toLowerCase() ?? DEFAULT_LOCALE;
  const resolved = (SUPPORTED_LOCALES as readonly string[]).includes(short)
    ? (short as Locale)
    : DEFAULT_LOCALE;
  return TODAY_MESSAGES[resolved][key] ?? TODAY_MESSAGES[DEFAULT_LOCALE][key] ?? key;
}
