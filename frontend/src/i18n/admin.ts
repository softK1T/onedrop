import type { Locale } from '@/i18n';

type AdminKeys =
  | 'profile.admin' | 'profile.loadFailed' | 'profile.defaultName'
  | 'admin.title' | 'admin.unauthorized' | 'admin.loadFailed' | 'admin.empty'
  | 'admin.users' | 'admin.failedCaptures' | 'admin.pendingNotifications'
  | 'admin.failedNotifications' | 'admin.aiOperations' | 'admin.aiCost'
  | 'admin.subscriptions' | 'admin.payments' | 'admin.stars' | 'admin.captureStatuses';

const en: Record<AdminKeys, string> = {
  'profile.admin': 'Administration', 'profile.loadFailed': 'Could not load profile.', 'profile.defaultName': 'OneDrop user',
  'admin.title': 'Administration', 'admin.unauthorized': 'You do not have administrator permission.', 'admin.loadFailed': 'Could not load operational data.', 'admin.empty': 'No operational data yet.',
  'admin.users': 'Users', 'admin.failedCaptures': 'Failed captures', 'admin.pendingNotifications': 'Due notifications', 'admin.failedNotifications': 'Failed notifications', 'admin.aiOperations': 'AI operations', 'admin.aiCost': 'AI cost (micro)', 'admin.subscriptions': 'Active subscriptions', 'admin.payments': 'Paid payments', 'admin.stars': 'Stars received', 'admin.captureStatuses': 'Captures by status',
};
const ru: Record<AdminKeys, string> = {
  'profile.admin': 'Администрирование', 'profile.loadFailed': 'Не удалось загрузить профиль.', 'profile.defaultName': 'Пользователь OneDrop',
  'admin.title': 'Администрирование', 'admin.unauthorized': 'У вас нет прав администратора.', 'admin.loadFailed': 'Не удалось загрузить служебные данные.', 'admin.empty': 'Служебных данных пока нет.',
  'admin.users': 'Пользователи', 'admin.failedCaptures': 'Ошибки обработки', 'admin.pendingNotifications': 'Ожидающие уведомления', 'admin.failedNotifications': 'Ошибки уведомлений', 'admin.aiOperations': 'AI-операции', 'admin.aiCost': 'Стоимость AI (micro)', 'admin.subscriptions': 'Активные подписки', 'admin.payments': 'Оплаченные платежи', 'admin.stars': 'Получено Stars', 'admin.captureStatuses': 'Обработки по статусам',
};
const pl: Record<AdminKeys, string> = {
  'profile.admin': 'Administracja', 'profile.loadFailed': 'Nie udało się wczytać profilu.', 'profile.defaultName': 'Użytkownik OneDrop',
  'admin.title': 'Administracja', 'admin.unauthorized': 'Nie masz uprawnień administratora.', 'admin.loadFailed': 'Nie udało się wczytać danych operacyjnych.', 'admin.empty': 'Brak danych operacyjnych.',
  'admin.users': 'Użytkownicy', 'admin.failedCaptures': 'Błędy przetwarzania', 'admin.pendingNotifications': 'Oczekujące powiadomienia', 'admin.failedNotifications': 'Błędy powiadomień', 'admin.aiOperations': 'Operacje AI', 'admin.aiCost': 'Koszt AI (micro)', 'admin.subscriptions': 'Aktywne subskrypcje', 'admin.payments': 'Opłacone płatności', 'admin.stars': 'Otrzymane Stars', 'admin.captureStatuses': 'Przechwycenia według statusu',
};
const uk: Record<AdminKeys, string> = {
  'profile.admin': 'Адміністрування', 'profile.loadFailed': 'Не вдалося завантажити профіль.', 'profile.defaultName': 'Користувач OneDrop',
  'admin.title': 'Адміністрування', 'admin.unauthorized': 'У вас немає прав адміністратора.', 'admin.loadFailed': 'Не вдалося завантажити службові дані.', 'admin.empty': 'Службових даних ще немає.',
  'admin.users': 'Користувачі', 'admin.failedCaptures': 'Помилки обробки', 'admin.pendingNotifications': 'Очікувані сповіщення', 'admin.failedNotifications': 'Помилки сповіщень', 'admin.aiOperations': 'AI-операції', 'admin.aiCost': 'Вартість AI (micro)', 'admin.subscriptions': 'Активні підписки', 'admin.payments': 'Оплачені платежі', 'admin.stars': 'Отримано Stars', 'admin.captureStatuses': 'Обробки за статусами',
};

export const ADMIN_MESSAGES: Record<Locale, Record<AdminKeys, string>> = { en, ru, pl, uk };
