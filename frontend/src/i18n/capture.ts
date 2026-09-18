import { DEFAULT_LOCALE, SUPPORTED_LOCALES, type Locale } from '@/i18n';

const en: Record<string, string> = {
  title: 'Capture',
  placeholder: 'Tomorrow at 15:00 meeting with Andrew, 45 PLN taxi',
  send: 'Send',
  voice: 'Voice',
  photo: 'Photo',
  processing: 'Parsing your message',
  created: 'Created',
  clarify: 'One question before saving',
  failed: 'Nothing was saved',
  fix: 'Fix',
  newCapture: 'New capture',
  structuredData: 'Structured capture data',
  structuredHint: 'Edit the detected fields as JSON. Keep at least one intent.',
  invalidCorrection: 'Enter valid JSON containing at least one intent.',
  saveCorrection: 'Save correction',
  saving: 'Saving…',
  saveFailed: 'The correction could not be saved.',
  cancel: 'Cancel',
};

const ru: Record<string, string> = {
  title: 'Новая запись',
  placeholder: 'Завтра в 15:00 встреча с Андреем, 45 PLN на такси',
  send: 'Отправить',
  voice: 'Голос',
  photo: 'Фото',
  processing: 'Разбираем сообщение',
  created: 'Создано',
  clarify: 'Один вопрос перед сохранением',
  failed: 'Ничего не сохранено',
  fix: 'Исправить',
  newCapture: 'Новая запись',
  structuredData: 'Структурированные данные',
  structuredHint: 'Исправьте распознанные поля в JSON. Оставьте хотя бы одно намерение.',
  invalidCorrection: 'Введите корректный JSON хотя бы с одним намерением.',
  saveCorrection: 'Сохранить исправление',
  saving: 'Сохраняем…',
  saveFailed: 'Не удалось сохранить исправление.',
  cancel: 'Отмена',
};

const pl: Record<string, string> = {
  title: 'Nowy wpis',
  placeholder: 'Jutro o 15:00 spotkanie z Andrzejem, 45 PLN za taksówkę',
  send: 'Wyślij',
  voice: 'Głos',
  photo: 'Zdjęcie',
  processing: 'Analizowanie wiadomości',
  created: 'Utworzono',
  clarify: 'Jedno pytanie przed zapisaniem',
  failed: 'Nic nie zapisano',
  fix: 'Popraw',
  newCapture: 'Nowy wpis',
  structuredData: 'Dane strukturalne wpisu',
  structuredHint: 'Popraw rozpoznane pola w JSON. Zachowaj co najmniej jedną intencję.',
  invalidCorrection: 'Wpisz poprawny JSON z co najmniej jedną intencją.',
  saveCorrection: 'Zapisz poprawkę',
  saving: 'Zapisywanie…',
  saveFailed: 'Nie udało się zapisać poprawki.',
  cancel: 'Anuluj',
};

const uk: Record<string, string> = {
  title: 'Новий запис',
  placeholder: 'Завтра о 15:00 зустріч з Андрієм, 45 PLN на таксі',
  send: 'Надіслати',
  voice: 'Голос',
  photo: 'Фото',
  processing: 'Розбираємо повідомлення',
  created: 'Створено',
  clarify: 'Одне запитання перед збереженням',
  failed: 'Нічого не збережено',
  fix: 'Виправити',
  newCapture: 'Новий запис',
  structuredData: 'Структуровані дані',
  structuredHint: 'Виправте розпізнані поля у JSON. Залиште хоча б один намір.',
  invalidCorrection: 'Введіть коректний JSON хоча б з одним наміром.',
  saveCorrection: 'Зберегти виправлення',
  saving: 'Зберігаємо…',
  saveFailed: 'Не вдалося зберегти виправлення.',
  cancel: 'Скасувати',
};

export const CAPTURE_MESSAGES: Record<Locale, Record<string, string>> = { en, ru, pl, uk };

export function captureLabel(locale: string | null | undefined, key: string): string {
  const short = (locale ?? DEFAULT_LOCALE).split('-')[0]?.toLowerCase() ?? DEFAULT_LOCALE;
  const resolved = (SUPPORTED_LOCALES as readonly string[]).includes(short)
    ? (short as Locale)
    : DEFAULT_LOCALE;
  return CAPTURE_MESSAGES[resolved][key] ?? CAPTURE_MESSAGES[DEFAULT_LOCALE][key] ?? key;
}
