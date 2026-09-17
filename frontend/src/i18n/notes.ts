import { DEFAULT_LOCALE, SUPPORTED_LOCALES, type Locale } from '@/i18n';

const en: Record<string, string> = {
  notes: 'Notes',
  searchLabel: 'Search notes',
  search: 'Search',
  clear: 'Clear',
  newNote: 'New note',
  noteTitle: 'Title',
  content: 'Note',
  contentPlaceholder: 'Anything you want to keep',
  tags: 'Tags, comma separated',
  add: 'Add note',
  edit: 'Edit',
  save: 'Save',
  cancel: 'Cancel',
  pin: 'Pin',
  unpin: 'Unpin',
  convert: 'Make a task',
  converted: 'A task was created from this note.',
  remove: 'Delete',
  empty: 'No notes yet.',
  noMatches: 'Nothing matches that search.',
  loadFailed: 'Could not load notes.',
  saveFailed: 'That change was not saved and has been reverted.',
  retry: 'Try again',
};

const ru: Record<string, string> = {
  notes: 'Заметки',
  searchLabel: 'Поиск по заметкам',
  search: 'Найти',
  clear: 'Сбросить',
  newNote: 'Новая заметка',
  noteTitle: 'Заголовок',
  content: 'Текст',
  contentPlaceholder: 'Всё, что хочется сохранить',
  tags: 'Теги через запятую',
  add: 'Добавить заметку',
  edit: 'Изменить',
  save: 'Сохранить',
  cancel: 'Отмена',
  pin: 'Закрепить',
  unpin: 'Открепить',
  convert: 'Сделать задачей',
  converted: 'Из заметки создана задача.',
  remove: 'Удалить',
  empty: 'Заметок пока нет.',
  noMatches: 'Ничего не нашлось.',
  loadFailed: 'Не удалось загрузить заметки.',
  saveFailed: 'Изменение не сохранено и было отменено.',
  retry: 'Повторить',
};

const pl: Record<string, string> = {
  notes: 'Notatki',
  searchLabel: 'Szukaj w notatkach',
  search: 'Szukaj',
  clear: 'Wyczyść',
  newNote: 'Nowa notatka',
  noteTitle: 'Tytuł',
  content: 'Treść',
  contentPlaceholder: 'Cokolwiek chcesz zachować',
  tags: 'Tagi po przecinku',
  add: 'Dodaj notatkę',
  edit: 'Edytuj',
  save: 'Zapisz',
  cancel: 'Anuluj',
  pin: 'Przypnij',
  unpin: 'Odepnij',
  convert: 'Zrób zadanie',
  converted: 'Z notatki powstało zadanie.',
  remove: 'Usuń',
  empty: 'Brak notatek.',
  noMatches: 'Nic nie pasuje do wyszukiwania.',
  loadFailed: 'Nie udało się wczytać notatek.',
  saveFailed: 'Zmiana nie została zapisana i została cofnięta.',
  retry: 'Spróbuj ponownie',
};

const uk: Record<string, string> = {
  notes: 'Замітки',
  searchLabel: 'Пошук у замітках',
  search: 'Шукати',
  clear: 'Очистити',
  newNote: 'Нова замітка',
  noteTitle: 'Заголовок',
  content: 'Текст',
  contentPlaceholder: 'Усе, що хочется зберегти',
  tags: 'Теги через кому',
  add: 'Додати замітку',
  edit: 'Змінити',
  save: 'Зберегти',
  cancel: 'Скасувати',
  pin: 'Закріпити',
  unpin: 'Відкріпити',
  convert: 'Зробити завданням',
  converted: 'Зі замітки створено завдання.',
  remove: 'Видалити',
  empty: 'Заміток ще немає.',
  noMatches: 'Нічого не знайдено.',
  loadFailed: 'Не вдалося завантажити замітки.',
  saveFailed: 'Зміна не збереглася і була скасована.',
  retry: 'Спробувати знову',
};

export const NOTE_MESSAGES: Record<Locale, Record<string, string>> = { en, ru, pl, uk };

export function noteLabel(locale: string | null | undefined, key: string): string {
  const short = (locale ?? DEFAULT_LOCALE).split('-')[0]?.toLowerCase() ?? DEFAULT_LOCALE;
  const resolved = (SUPPORTED_LOCALES as readonly string[]).includes(short)
    ? (short as Locale)
    : DEFAULT_LOCALE;
  return NOTE_MESSAGES[resolved][key] ?? NOTE_MESSAGES[DEFAULT_LOCALE][key] ?? key;
}
