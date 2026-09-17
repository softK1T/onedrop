import { DEFAULT_LOCALE, SUPPORTED_LOCALES, type Locale } from '@/i18n';

const en: Record<string, string> = {
  title: 'Settings',
  loadFailed: 'Could not load settings.',
  saveFailed: 'Could not save that change. It was reverted.',
  retry: 'Try again',
  general: 'General',
  timezone: 'Timezone',
  currency: 'Currency',
  budget: 'Monthly budget',
  reminders: 'Reminders',
  remindersHint: 'Turn everything off to stop all notifications.',
  morningDigest: 'Morning digest',
  digestHour: 'Digest hour',
  taskReminders: 'Task reminders',
  taskLead: 'Task lead time, minutes',
  eventReminders: 'Event reminders',
  eventLead: 'Event lead time, minutes',
  habitReminders: 'Habit reminders',
  budgetWarnings: 'Budget warnings',
  budgetThreshold: 'Warn at percent of budget',
  quietHours: 'Quiet hours',
  quietFrom: 'Quiet from',
  quietTo: 'Quiet until',
  quietHint: 'Set both to the same hour to disable quiet hours.',
};

const ru: Record<string, string> = {
  title: 'Настройки',
  loadFailed: 'Не удалось загрузить настройки.',
  saveFailed: 'Не удалось сохранить изменение, оно отменено.',
  retry: 'Повторить',
  general: 'Основное',
  timezone: 'Часовой пояс',
  currency: 'Валюта',
  budget: 'Бюджет на месяц',
  reminders: 'Напоминания',
  remindersHint: 'Выключите всё, чтобы не получать уведомления.',
  morningDigest: 'Утренняя сводка',
  digestHour: 'Час сводки',
  taskReminders: 'Напоминания о задачах',
  taskLead: 'Заранее для задач, минут',
  eventReminders: 'Напоминания о событиях',
  eventLead: 'Заранее для событий, минут',
  habitReminders: 'Напоминания о привычках',
  budgetWarnings: 'Предупреждения о бюджете',
  budgetThreshold: 'Предупреждать при проценте бюджета',
  quietHours: 'Тихие часы',
  quietFrom: 'Тихо с',
  quietTo: 'Тихо до',
  quietHint: 'Одинаковые значения отключают тихие часы.',
};

const pl: Record<string, string> = {
  title: 'Ustawienia',
  loadFailed: 'Nie udało się wczytać ustawień.',
  saveFailed: 'Nie udało się zapisać zmiany, została cofnięta.',
  retry: 'Spróbuj ponownie',
  general: 'Ogólne',
  timezone: 'Strefa czasowa',
  currency: 'Waluta',
  budget: 'Budżet miesięczny',
  reminders: 'Przypomnienia',
  remindersHint: 'Wyłącz wszystko, aby nie dostawać powiadomień.',
  morningDigest: 'Poranne podsumowanie',
  digestHour: 'Godzina podsumowania',
  taskReminders: 'Przypomnienia o zadaniach',
  taskLead: 'Wyprzedzenie dla zadań, minuty',
  eventReminders: 'Przypomnienia o wydarzeniach',
  eventLead: 'Wyprzedzenie dla wydarzeń, minuty',
  habitReminders: 'Przypomnienia o nawykach',
  budgetWarnings: 'Ostrzeżenia budżetowe',
  budgetThreshold: 'Ostrzegaj przy procencie budżetu',
  quietHours: 'Ciche godziny',
  quietFrom: 'Cisza od',
  quietTo: 'Cisza do',
  quietHint: 'Te same wartości wyłączają ciche godziny.',
};

const uk: Record<string, string> = {
  title: 'Налаштування',
  loadFailed: 'Не вдалося завантажити налаштування.',
  saveFailed: 'Не вдалося зберегти зміну, її скасовано.',
  retry: 'Спробувати знову',
  general: 'Загальне',
  timezone: 'Часовий пояс',
  currency: 'Валюта',
  budget: 'Бюджет на місяць',
  reminders: 'Нагадування',
  remindersHint: 'Вимкніть усе, щоб не отримувати повідомлення.',
  morningDigest: 'Ранкове зведення',
  digestHour: 'Година зведення',
  taskReminders: 'Нагадування про завдання',
  taskLead: 'Заздалегідь для завдань, хвилин',
  eventReminders: 'Нагадування про події',
  eventLead: 'Заздалегідь для подій, хвилин',
  habitReminders: 'Нагадування про звички',
  budgetWarnings: 'Попередження про бюджет',
  budgetThreshold: 'Попереджати за відсотком бюджету',
  quietHours: 'Тихі години',
  quietFrom: 'Тихо з',
  quietTo: 'Тихо до',
  quietHint: 'Однакові значення вимикають тихі години.',
};

export const SETTINGS_MESSAGES: Record<Locale, Record<string, string>> = { en, ru, pl, uk };

export function settingsLabel(locale: string | null | undefined, key: string): string {
  const short = (locale ?? DEFAULT_LOCALE).split('-')[0]?.toLowerCase() ?? DEFAULT_LOCALE;
  const resolved = (SUPPORTED_LOCALES as readonly string[]).includes(short)
    ? (short as Locale)
    : DEFAULT_LOCALE;
  return SETTINGS_MESSAGES[resolved][key] ?? SETTINGS_MESSAGES[DEFAULT_LOCALE][key] ?? key;
}
