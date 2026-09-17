import { DEFAULT_LOCALE, SUPPORTED_LOCALES, type Locale } from '@/i18n';

const en: Record<string, string> = {
  events: 'Events',
  day: 'Day',
  week: 'Week',
  date: 'Date',
  newEvent: 'New event',
  eventTitle: 'Title',
  starts: 'Starts',
  ends: 'Ends',
  location: 'Location',
  add: 'Add event',
  edit: 'Edit',
  save: 'Save',
  cancel: 'Cancel',
  complete: 'Done',
  cancelEvent: 'Cancel event',
  remove: 'Delete',
  conflict: 'This event overlaps another one. Nothing was blocked.',
  empty: 'Nothing scheduled for this period.',
  loadFailed: 'Could not load events.',
  saveFailed: 'That change was not saved and has been reverted.',
  retry: 'Try again',
  statusCancelled: 'cancelled',
  statusDone: 'done',
};

const ru: Record<string, string> = {
  events: 'События',
  day: 'День',
  week: 'Неделя',
  date: 'Дата',
  newEvent: 'Новое событие',
  eventTitle: 'Название',
  starts: 'Начало',
  ends: 'Конец',
  location: 'Место',
  add: 'Добавить событие',
  edit: 'Изменить',
  save: 'Сохранить',
  cancel: 'Отмена',
  complete: 'Готово',
  cancelEvent: 'Отменить событие',
  remove: 'Удалить',
  conflict: 'Событие пересекается с другим. Ничего не заблокировано.',
  empty: 'На этот период ничего не запланировано.',
  loadFailed: 'Не удалось загрузить события.',
  saveFailed: 'Изменение не сохранено и было отменено.',
  retry: 'Повторить',
  statusCancelled: 'отменено',
  statusDone: 'завершено',
};

const pl: Record<string, string> = {
  events: 'Wydarzenia',
  day: 'Dzień',
  week: 'Tydzień',
  date: 'Data',
  newEvent: 'Nowe wydarzenie',
  eventTitle: 'Nazwa',
  starts: 'Początek',
  ends: 'Koniec',
  location: 'Miejsce',
  add: 'Dodaj wydarzenie',
  edit: 'Edytuj',
  save: 'Zapisz',
  cancel: 'Anuluj',
  complete: 'Gotowe',
  cancelEvent: 'Odwołaj wydarzenie',
  remove: 'Usuń',
  conflict: 'To wydarzenie nakłada się na inne. Nic nie zostało zablokowane.',
  empty: 'Nic nie zaplanowano na ten okres.',
  loadFailed: 'Nie udało się wczytać wydarzeń.',
  saveFailed: 'Zmiana nie została zapisana i została cofnięta.',
  retry: 'Spróbuj ponownie',
  statusCancelled: 'odwołane',
  statusDone: 'zakończone',
};

const uk: Record<string, string> = {
  events: 'Події',
  day: 'День',
  week: 'Тиждень',
  date: 'Дата',
  newEvent: 'Нова подія',
  eventTitle: 'Назва',
  starts: 'Початок',
  ends: 'Завершення',
  location: 'Місце',
  add: 'Додати подію',
  edit: 'Змінити',
  save: 'Зберегти',
  cancel: 'Скасувати',
  complete: 'Готово',
  cancelEvent: 'Скасувати подію',
  remove: 'Видалити',
  conflict: 'Подія перетинається з іншою. Нічого не заблоковано.',
  empty: 'На цей період нічого не заплановано.',
  loadFailed: 'Не вдалося завантажити події.',
  saveFailed: 'Зміна не збереглася і була скасована.',
  retry: 'Спробувати знову',
  statusCancelled: 'скасовано',
  statusDone: 'завершено',
};

export const EVENT_MESSAGES: Record<Locale, Record<string, string>> = { en, ru, pl, uk };

export function eventLabel(locale: string | null | undefined, key: string): string {
  const short = (locale ?? DEFAULT_LOCALE).split('-')[0]?.toLowerCase() ?? DEFAULT_LOCALE;
  const resolved = (SUPPORTED_LOCALES as readonly string[]).includes(short)
    ? (short as Locale)
    : DEFAULT_LOCALE;
  return EVENT_MESSAGES[resolved][key] ?? EVENT_MESSAGES[DEFAULT_LOCALE][key] ?? key;
}
