import { ADMIN_MESSAGES } from '@/i18n/admin';

export const SUPPORTED_LOCALES = ['en', 'ru', 'pl', 'uk'] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];
export const DEFAULT_LOCALE: Locale = 'en';

type CoreKey =
  | 'nav.main' | 'nav.today' | 'nav.inbox' | 'nav.add' | 'nav.analytics' | 'nav.profile'
  | 'app.loading' | 'app.authFailed' | 'app.devLogin' | 'app.retry'
  | 'today.title' | 'today.empty' | 'today.tasks' | 'today.events' | 'today.spent'
  | 'today.calories' | 'today.aiLeft' | 'today.budgetWarning'
  | 'inbox.title' | 'inbox.empty' | 'inbox.retry' | 'inbox.undo'
  | 'capture.title' | 'capture.placeholder' | 'capture.send' | 'capture.voice'
  | 'capture.photo' | 'capture.processing' | 'capture.created' | 'capture.clarify'
  | 'capture.failed' | 'capture.fix' | 'analytics.title' | 'analytics.expenses'
  | 'analytics.nutrition' | 'analytics.habits' | 'analytics.productivity' | 'analytics.noData'
  | 'profile.title' | 'profile.settings' | 'profile.subscription' | 'profile.privacy'
  | 'profile.export' | 'profile.delete' | 'profile.deleteConfirm'
  | 'subscription.free' | 'subscription.pro' | 'subscription.upgrade' | 'subscription.price'
  | 'entity.task' | 'entity.event' | 'entity.expense' | 'entity.meal' | 'entity.habit'
  | 'entity.habit_log' | 'entity.note' | 'common.save' | 'common.cancel'
  | 'common.delete' | 'common.estimated' | 'common.error';

const en: Record<CoreKey, string> = {
  'nav.main':'Main navigation','nav.today':'Today','nav.inbox':'Inbox','nav.add':'Add','nav.analytics':'Analytics','nav.profile':'Profile',
  'app.loading':'Loading OneDrop','app.authFailed':'Could not sign you in','app.devLogin':'Continue with dev login','app.retry':'Try again',
  'today.title':'Today','today.empty':'Nothing planned yet. Capture something below.','today.tasks':'Tasks','today.events':'Events','today.spent':'Spent today','today.calories':'Calories','today.aiLeft':'AI actions left','today.budgetWarning':'You are close to your monthly budget',
  'inbox.title':'Inbox','inbox.empty':'No captures yet.','inbox.retry':'Retry','inbox.undo':'Undo all',
  'capture.title':'Capture','capture.placeholder':'Tomorrow at 15:00 meeting with Andrew, 45 PLN taxi','capture.send':'Send','capture.voice':'Voice','capture.photo':'Photo','capture.processing':'Parsing your message','capture.created':'Created','capture.clarify':'One question before saving','capture.failed':'Nothing was saved','capture.fix':'Fix',
  'analytics.title':'Analytics','analytics.expenses':'Expenses','analytics.nutrition':'Nutrition','analytics.habits':'Habits','analytics.productivity':'Productivity','analytics.noData':'Not enough data yet.',
  'profile.title':'Profile','profile.settings':'Settings','profile.subscription':'Subscription','profile.privacy':'Privacy','profile.export':'Export my data','profile.delete':'Delete account','profile.deleteConfirm':'This deletes every record and all media. It cannot be undone.',
  'subscription.free':'Free plan','subscription.pro':'Pro plan','subscription.upgrade':'Get Pro','subscription.price':'{price} Stars per {days} days',
  'entity.task':'Task','entity.event':'Event','entity.expense':'Expense','entity.meal':'Meal','entity.habit':'Habit','entity.habit_log':'Habit check-in','entity.note':'Note',
  'common.save':'Save','common.cancel':'Cancel','common.delete':'Delete','common.estimated':'approximate','common.error':'Something went wrong',
};
const ru: Record<CoreKey, string> = {
  'nav.main':'Основная навигация','nav.today':'Сегодня','nav.inbox':'Входящие','nav.add':'Добавить','nav.analytics':'Аналитика','nav.profile':'Профиль',
  'app.loading':'Загрузка OneDrop','app.authFailed':'Не удалось войти','app.devLogin':'Продолжить в dev-режиме','app.retry':'Повторить',
  'today.title':'Сегодня','today.empty':'Пока ничего не запланировано. Добавьте запись ниже.','today.tasks':'Задачи','today.events':'События','today.spent':'Потрачено сегодня','today.calories':'Калории','today.aiLeft':'Осталось AI-действий','today.budgetWarning':'Вы приближаетесь к месячному бюджету',
  'inbox.title':'Входящие','inbox.empty':'Записей пока нет.','inbox.retry':'Повторить','inbox.undo':'Отменить всё',
  'capture.title':'Новая запись','capture.placeholder':'Завтра в 15:00 встреча с Андреем, такси 45 PLN','capture.send':'Отправить','capture.voice':'Голос','capture.photo':'Фото','capture.processing':'Разбираем сообщение','capture.created':'Создано','capture.clarify':'Один вопрос перед сохранением','capture.failed':'Ничего не сохранено','capture.fix':'Исправить',
  'analytics.title':'Аналитика','analytics.expenses':'Расходы','analytics.nutrition':'Питание','analytics.habits':'Привычки','analytics.productivity':'Продуктивность','analytics.noData':'Данных пока недостаточно.',
  'profile.title':'Профиль','profile.settings':'Настройки','profile.subscription':'Подписка','profile.privacy':'Приватность','profile.export':'Экспортировать данные','profile.delete':'Удалить аккаунт','profile.deleteConfirm':'Все записи и медиа будут удалены без возможности восстановления.',
  'subscription.free':'Тариф Free','subscription.pro':'Тариф Pro','subscription.upgrade':'Подключить Pro','subscription.price':'{price} Stars за {days} дней',
  'entity.task':'Задача','entity.event':'Событие','entity.expense':'Расход','entity.meal':'Приём пищи','entity.habit':'Привычка','entity.habit_log':'Отметка привычки','entity.note':'Заметка',
  'common.save':'Сохранить','common.cancel':'Отмена','common.delete':'Удалить','common.estimated':'приблизительно','common.error':'Что-то пошло не так',
};
const pl: Record<CoreKey, string> = {
  'nav.main':'Główna nawigacja','nav.today':'Dzisiaj','nav.inbox':'Skrzynka','nav.add':'Dodaj','nav.analytics':'Analityka','nav.profile':'Profil',
  'app.loading':'Wczytywanie OneDrop','app.authFailed':'Nie udało się zalogować','app.devLogin':'Kontynuuj w trybie dev','app.retry':'Spróbuj ponownie',
  'today.title':'Dzisiaj','today.empty':'Nic jeszcze nie zaplanowano. Dodaj wpis poniżej.','today.tasks':'Zadania','today.events':'Wydarzenia','today.spent':'Wydano dzisiaj','today.calories':'Kalorie','today.aiLeft':'Pozostałe akcje AI','today.budgetWarning':'Zbliżasz się do miesięcznego budżetu',
  'inbox.title':'Skrzynka','inbox.empty':'Brak wpisów.','inbox.retry':'Ponów','inbox.undo':'Cofnij wszystko',
  'capture.title':'Nowy wpis','capture.placeholder':'Jutro o 15:00 spotkanie z Andrzejem, taksówka 45 PLN','capture.send':'Wyślij','capture.voice':'Głos','capture.photo':'Zdjęcie','capture.processing':'Analizowanie wiadomości','capture.created':'Utworzono','capture.clarify':'Jedno pytanie przed zapisem','capture.failed':'Nic nie zapisano','capture.fix':'Popraw',
  'analytics.title':'Analityka','analytics.expenses':'Wydatki','analytics.nutrition':'Odżywianie','analytics.habits':'Nawyki','analytics.productivity':'Produktywność','analytics.noData':'Za mało danych.',
  'profile.title':'Profil','profile.settings':'Ustawienia','profile.subscription':'Subskrypcja','profile.privacy':'Prywatność','profile.export':'Eksportuj dane','profile.delete':'Usuń konto','profile.deleteConfirm':'Wszystkie wpisy i multimedia zostaną bezpowrotnie usunięte.',
  'subscription.free':'Plan Free','subscription.pro':'Plan Pro','subscription.upgrade':'Włącz Pro','subscription.price':'{price} Stars za {days} dni',
  'entity.task':'Zadanie','entity.event':'Wydarzenie','entity.expense':'Wydatek','entity.meal':'Posiłek','entity.habit':'Nawyk','entity.habit_log':'Wykonanie nawyku','entity.note':'Notatka',
  'common.save':'Zapisz','common.cancel':'Anuluj','common.delete':'Usuń','common.estimated':'szacunkowo','common.error':'Coś poszło nie tak',
};
const uk: Record<CoreKey, string> = {
  'nav.main':'Основна навігація','nav.today':'Сьогодні','nav.inbox':'Вхідні','nav.add':'Додати','nav.analytics':'Аналітика','nav.profile':'Профіль',
  'app.loading':'Завантаження OneDrop','app.authFailed':'Не вдалося увійти','app.devLogin':'Продовжити в dev-режимі','app.retry':'Спробувати знову',
  'today.title':'Сьогодні','today.empty':'Поки нічого не заплановано. Додайте запис нижче.','today.tasks':'Завдання','today.events':'Події','today.spent':'Витрачено сьогодні','today.calories':'Калорії','today.aiLeft':'Залишилося AI-дій','today.budgetWarning':'Ви наближаєтеся до місячного бюджету',
  'inbox.title':'Вхідні','inbox.empty':'Записів поки немає.','inbox.retry':'Повторити','inbox.undo':'Скасувати все',
  'capture.title':'Новий запис','capture.placeholder':'Завтра о 15:00 зустріч з Андрієм, таксі 45 PLN','capture.send':'Надіслати','capture.voice':'Голос','capture.photo':'Фото','capture.processing':'Аналізуємо повідомлення','capture.created':'Створено','capture.clarify':'Одне питання перед збереженням','capture.failed':'Нічого не збережено','capture.fix':'Виправити',
  'analytics.title':'Аналітика','analytics.expenses':'Витрати','analytics.nutrition':'Харчування','analytics.habits':'Звички','analytics.productivity':'Продуктивність','analytics.noData':'Даних поки недостатньо.',
  'profile.title':'Профіль','profile.settings':'Налаштування','profile.subscription':'Підписка','profile.privacy':'Приватність','profile.export':'Експортувати дані','profile.delete':'Видалити акаунт','profile.deleteConfirm':'Усі записи й медіа буде видалено без можливості відновлення.',
  'subscription.free':'Тариф Free','subscription.pro':'Тариф Pro','subscription.upgrade':'Підключити Pro','subscription.price':'{price} Stars за {days} днів',
  'entity.task':'Завдання','entity.event':'Подія','entity.expense':'Витрата','entity.meal':'Прийом їжі','entity.habit':'Звичка','entity.habit_log':'Відмітка звички','entity.note':'Нотатка',
  'common.save':'Зберегти','common.cancel':'Скасувати','common.delete':'Видалити','common.estimated':'приблизно','common.error':'Щось пішло не так',
};

const CORE_MESSAGES: Record<Locale, Record<CoreKey, string>> = { en, ru, pl, uk };
export const MESSAGES: Record<Locale, Record<string, string>> = {
  en: { ...CORE_MESSAGES.en, ...ADMIN_MESSAGES.en },
  ru: { ...CORE_MESSAGES.ru, ...ADMIN_MESSAGES.ru },
  pl: { ...CORE_MESSAGES.pl, ...ADMIN_MESSAGES.pl },
  uk: { ...CORE_MESSAGES.uk, ...ADMIN_MESSAGES.uk },
};

export function normaliseLocale(locale: string | null | undefined): Locale {
  if (!locale) return DEFAULT_LOCALE;
  const short = locale.split('-')[0]?.toLowerCase() ?? '';
  return (SUPPORTED_LOCALES as readonly string[]).includes(short) ? short as Locale : DEFAULT_LOCALE;
}

export function translate(locale: Locale, key: string, values?: Record<string, string | number>): string {
  const template = MESSAGES[locale][key] ?? MESSAGES.en[key] ?? key;
  if (!values) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) => values[name] === undefined ? match : String(values[name]));
}
