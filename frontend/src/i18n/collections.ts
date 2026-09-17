import { DEFAULT_LOCALE, SUPPORTED_LOCALES, type Locale } from '@/i18n';

const en: Record<string, string> = {
  tasks: 'Tasks',
  filterToday: 'Today',
  filterUpcoming: 'Upcoming',
  filterNoDate: 'No date',
  filterCompleted: 'Completed',
  filterAll: 'All',
  newTask: 'New task',
  titlePlaceholder: 'What needs to be done?',
  due: 'Due',
  priority: 'Priority',
  priorityLow: 'Low',
  priorityNormal: 'Normal',
  priorityHigh: 'High',
  add: 'Add task',
  edit: 'Edit',
  save: 'Save',
  cancel: 'Cancel',
  complete: 'Done',
  remove: 'Delete',
  empty: 'Nothing here yet. Add a task or capture one.',
  loadFailed: 'Could not load tasks.',
  saveFailed: 'That change was not saved and has been reverted.',
  retry: 'Try again',
};

const ru: Record<string, string> = {
  tasks: 'Задачи',
  filterToday: 'Сегодня',
  filterUpcoming: 'Дальше',
  filterNoDate: 'Без даты',
  filterCompleted: 'Выполненные',
  filterAll: 'Все',
  newTask: 'Новая задача',
  titlePlaceholder: 'Что нужно сделать?',
  due: 'Срок',
  priority: 'Приоритет',
  priorityLow: 'Низкий',
  priorityNormal: 'Обычный',
  priorityHigh: 'Высокий',
  add: 'Добавить задачу',
  edit: 'Изменить',
  save: 'Сохранить',
  cancel: 'Отмена',
  complete: 'Готово',
  remove: 'Удалить',
  empty: 'Пока пусто. Добавьте задачу или запишите её через capture.',
  loadFailed: 'Не удалось загрузить задачи.',
  saveFailed: 'Изменение не сохранено и было отменено.',
  retry: 'Повторить',
};

const pl: Record<string, string> = {
  tasks: 'Zadania',
  filterToday: 'Dzisiaj',
  filterUpcoming: 'Nadchodzące',
  filterNoDate: 'Bez daty',
  filterCompleted: 'Zrobione',
  filterAll: 'Wszystkie',
  newTask: 'Nowe zadanie',
  titlePlaceholder: 'Co trzeba zrobić?',
  due: 'Termin',
  priority: 'Priorytet',
  priorityLow: 'Niski',
  priorityNormal: 'Zwykły',
  priorityHigh: 'Wysoki',
  add: 'Dodaj zadanie',
  edit: 'Edytuj',
  save: 'Zapisz',
  cancel: 'Anuluj',
  complete: 'Gotowe',
  remove: 'Usuń',
  empty: 'Na razie pusto. Dodaj zadanie lub zapisz je przez capture.',
  loadFailed: 'Nie udało się wczytać zadań.',
  saveFailed: 'Zmiana nie została zapisana i została cofnięta.',
  retry: 'Spróbuj ponownie',
};

const uk: Record<string, string> = {
  tasks: 'Завдання',
  filterToday: 'Сьогодні',
  filterUpcoming: 'Надалі',
  filterNoDate: 'Без дати',
  filterCompleted: 'Виконані',
  filterAll: 'Усі',
  newTask: 'Нове завдання',
  titlePlaceholder: 'Що потрібно зробити?',
  due: 'Термін',
  priority: 'Пріоритет',
  priorityLow: 'Низький',
  priorityNormal: 'Звичайний',
  priorityHigh: 'Високий',
  add: 'Додати завдання',
  edit: 'Змінити',
  save: 'Зберегти',
  cancel: 'Скасувати',
  complete: 'Готово',
  remove: 'Видалити',
  empty: 'Поки порожньо. Додайте завдання або запишіть його через capture.',
  loadFailed: 'Не вдалося завантажити завдання.',
  saveFailed: 'Зміна не збереглася і була скасована.',
  retry: 'Спробувати знову',
};

export const COLLECTION_MESSAGES: Record<Locale, Record<string, string>> = { en, ru, pl, uk };

export function collectionLabel(locale: string | null | undefined, key: string): string {
  const short = (locale ?? DEFAULT_LOCALE).split('-')[0]?.toLowerCase() ?? DEFAULT_LOCALE;
  const resolved = (SUPPORTED_LOCALES as readonly string[]).includes(short)
    ? (short as Locale)
    : DEFAULT_LOCALE;
  return COLLECTION_MESSAGES[resolved][key] ?? COLLECTION_MESSAGES[DEFAULT_LOCALE][key] ?? key;
}
