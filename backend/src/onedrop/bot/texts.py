"""Bot copy in four languages.

Strings live here, never inside handlers, and are never translated at runtime by
an LLM. Every locale carries the same keys; a unit test enforces that.
"""

from __future__ import annotations

from typing import Any

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES: tuple[str, ...] = ("en", "ru", "pl", "uk")

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "start_welcome": (
            "OneDrop turns anything you drop here into structured records.\n\n"
            "Send a sentence, a voice message or a photo of your food. I will create "
            "tasks, events, expenses, meals, habits and notes for you."
        ),
        "onboarding_consent": (
            "Before the first AI request I need your consent to process the text, "
            "voice and photos you send. You can export or delete everything at any "
            "time."
        ),
        "onboarding_done": "All set. Try: 'Tomorrow at 15:00 meeting with Andrew'.",
        "help": (
            "Commands:\n"
            "/today - today overview\n"
            "/plan - plan your day\n"
            "/settings - preferences and reminders\n"
            "/help - this message\n\n"
            "Just send text, voice or a food photo to capture something."
        ),
        "ack": "Accepted, parsing your message...",
        "today_header": "Today",
        "today_empty": "Nothing planned yet. Send something to capture.",
        "plan_prompt": (
            "What is on your plate? Send it in one message: tasks, meetings, "
            "expenses. I will split it up."
        ),
        "settings_header": "Settings",
        "settings_body": (
            "Timezone: {timezone}\nCurrency: {currency}\nReminders: {reminders}\n"
            "Plan: {plan}"
        ),
        "limit_left": "AI actions left: {remaining}",
        "limit_reached": (
            "Daily AI limit reached. It resets tomorrow, or you can switch to Pro."
        ),
        "paywall": (
            "Pro unlocks food photo recognition, the morning digest, advanced "
            "analytics, CSV export and a monthly AI allowance for {price} Stars per "
            "{days} days."
        ),
        "result_header": "Created:",
        "result_empty": "I could not find anything to save in that message.",
        "needs_confirmation": "One thing before I save it: {question}",
        "undo_done": "Undone. {count} record(s) removed.",
        "error_generic": "Something went wrong. Nothing was saved. Try again.",
        "unsupported": "I can handle text, voice messages and photos.",
        "button_open": "Open",
        "button_fix": "Fix",
        "button_undo": "Undo all",
        "button_buy_pro": "Get Pro",
        "button_consent": "I agree",
        "button_privacy": "Privacy",
    },
    "ru": {
        "start_welcome": (
            "OneDrop \u043f\u0440\u0435\u0432\u0440\u0430\u0449\u0430\u0435\u0442 \u0432\u0441\u0451, \u0447\u0442\u043e \u0432\u044b \u0441\u044e\u0434\u0430 \u043f\u0440\u0438\u0441\u043b\u0430\u043b\u0438, \u0432 "
            "\u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u043d\u044b\u0435 \u0437\u0430\u043f\u0438\u0441\u0438.\n\n"
            "\u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0442\u0435\u043a\u0441\u0442, \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u043e\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0438\u043b\u0438 \u0444\u043e\u0442\u043e \u0435\u0434\u044b. "
            "\u042f \u0441\u043e\u0437\u0434\u0430\u043c \u0437\u0430\u0434\u0430\u0447\u0438, \u0441\u043e\u0431\u044b\u0442\u0438\u044f, \u0440\u0430\u0441\u0445\u043e\u0434\u044b, \u043f\u0440\u0438\u0451\u043c\u044b \u043f\u0438\u0449\u0438, "
            "\u043f\u0440\u0438\u0432\u044b\u0447\u043a\u0438 \u0438 \u0437\u0430\u043c\u0435\u0442\u043a\u0438."
        ),
        "onboarding_consent": (
            "\u041f\u0435\u0440\u0435\u0434 \u043f\u0435\u0440\u0432\u044b\u043c AI-\u0437\u0430\u043f\u0440\u043e\u0441\u043e\u043c \u043d\u0443\u0436\u043d\u043e \u0432\u0430\u0448\u0435 \u0441\u043e\u0433\u043b\u0430\u0441\u0438\u0435 \u043d\u0430 "
            "\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0443 \u0442\u0435\u043a\u0441\u0442\u0430, \u0433\u043e\u043b\u043e\u0441\u0430 \u0438 \u0444\u043e\u0442\u043e. \u0414\u0430\u043d\u043d\u044b\u0435 \u043c\u043e\u0436\u043d\u043e "
            "\u0432\u044b\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0438\u043b\u0438 \u0443\u0434\u0430\u043b\u0438\u0442\u044c \u0432 \u043b\u044e\u0431\u043e\u0439 \u043c\u043e\u043c\u0435\u043d\u0442."
        ),
        "onboarding_done": (
            "\u0413\u043e\u0442\u043e\u0432\u043e. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435: \u00ab\u0417\u0430\u0432\u0442\u0440\u0430 \u0432 15:00 \u0432\u0441\u0442\u0440\u0435\u0447\u0430 \u0441 \u0410\u043d\u0434\u0440\u0435\u0435\u043c\u00bb."
        ),
        "help": (
            "\u041a\u043e\u043c\u0430\u043d\u0434\u044b:\n"
            "/today - \u043e\u0431\u0437\u043e\u0440 \u0434\u043d\u044f\n"
            "/plan - \u0441\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0434\u0435\u043d\u044c\n"
            "/settings - \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u0438 \u043d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f\n"
            "/help - \u044d\u0442\u043e \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435\n\n"
            "\u041f\u0440\u043e\u0441\u0442\u043e \u043f\u0440\u0438\u0448\u043b\u0438\u0442\u0435 \u0442\u0435\u043a\u0441\u0442, \u0433\u043e\u043b\u043e\u0441 \u0438\u043b\u0438 \u0444\u043e\u0442\u043e \u0435\u0434\u044b."
        ),
        "ack": "\u041f\u0440\u0438\u043d\u044f\u0442\u043e, \u0440\u0430\u0437\u0431\u0438\u0440\u0430\u044e \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435...",
        "today_header": "\u0421\u0435\u0433\u043e\u0434\u043d\u044f",
        "today_empty": (
            "\u041f\u043b\u0430\u043d\u043e\u0432 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442. \u041f\u0440\u0438\u0448\u043b\u0438\u0442\u0435 \u0447\u0442\u043e-\u043d\u0438\u0431\u0443\u0434\u044c \u2014 \u044f \u0441\u043e\u0445\u0440\u0430\u043d\u044e."
        ),
        "plan_prompt": (
            "\u0427\u0442\u043e \u0432 \u043f\u043b\u0430\u043d\u0430\u0445? \u041f\u0440\u0438\u0448\u043b\u0438\u0442\u0435 \u043e\u0434\u043d\u0438\u043c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435\u043c: \u0437\u0430\u0434\u0430\u0447\u0438, "
            "\u0432\u0441\u0442\u0440\u0435\u0447\u0438, \u0440\u0430\u0441\u0445\u043e\u0434\u044b. \u042f \u0440\u0430\u0437\u043b\u043e\u0436\u0443 \u043f\u043e \u043f\u043e\u043b\u043e\u0447\u043a\u0430\u043c."
        ),
        "settings_header": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438",
        "settings_body": (
            "\u0422\u0430\u0439\u043c\u0437\u043e\u043d\u0430: {timezone}\n\u0412\u0430\u043b\u044e\u0442\u0430: {currency}\n"
            "\u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f: {reminders}\n\u0422\u0430\u0440\u0438\u0444: {plan}"
        ),
        "limit_left": "\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c AI-\u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0439: {remaining}",
        "limit_reached": (
            "\u0414\u043d\u0435\u0432\u043d\u043e\u0439 \u043b\u0438\u043c\u0438\u0442 AI \u0438\u0441\u0447\u0435\u0440\u043f\u0430\u043d. \u041e\u043d \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u0441\u044f \u0437\u0430\u0432\u0442\u0440\u0430, "
            "\u0438\u043b\u0438 \u043f\u0435\u0440\u0435\u0445\u043e\u0434\u0438\u0442\u0435 \u043d\u0430 Pro."
        ),
        "paywall": (
            "Pro \u043e\u0442\u043a\u0440\u044b\u0432\u0430\u0435\u0442 \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u0432\u0430\u043d\u0438\u0435 \u0444\u043e\u0442\u043e \u0435\u0434\u044b, \u0443\u0442\u0440\u0435\u043d\u043d\u0438\u0439 \u043e\u0431\u0437\u043e\u0440, "
            "\u0440\u0430\u0441\u0448\u0438\u0440\u0435\u043d\u043d\u0443\u044e \u0430\u043d\u0430\u043b\u0438\u0442\u0438\u043a\u0443, \u044d\u043a\u0441\u043f\u043e\u0440\u0442 CSV \u0438 \u043c\u0435\u0441\u044f\u0447\u043d\u044b\u0439 AI-\u043b\u0438\u043c\u0438\u0442 "
            "\u0437\u0430 {price} Stars \u043d\u0430 {days} \u0434\u043d\u0435\u0439."
        ),
        "result_header": "\u0421\u043e\u0437\u0434\u0430\u043d\u043e:",
        "result_empty": (
            "\u0412 \u044d\u0442\u043e\u043c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0438 \u043d\u0435 \u043d\u0430\u0448\u043b\u043e\u0441\u044c, \u0447\u0442\u043e \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c."
        ),
        "needs_confirmation": "\u0423\u0442\u043e\u0447\u043d\u0438\u0442\u0435, \u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430: {question}",
        "undo_done": "\u041e\u0442\u043c\u0435\u043d\u0435\u043d\u043e. \u0423\u0434\u0430\u043b\u0435\u043d\u043e \u0437\u0430\u043f\u0438\u0441\u0435\u0439: {count}.",
        "error_generic": (
            "\u0427\u0442\u043e-\u0442\u043e \u043f\u043e\u0448\u043b\u043e \u043d\u0435 \u0442\u0430\u043a. \u041d\u0438\u0447\u0435\u0433\u043e \u043d\u0435 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0441\u043d\u043e\u0432\u0430."
        ),
        "unsupported": (
            "\u042f \u043f\u043e\u043d\u0438\u043c\u0430\u044e \u0442\u0435\u043a\u0441\u0442, \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u044b\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u044f \u0438 \u0444\u043e\u0442\u043e."
        ),
        "button_open": "\u041e\u0442\u043a\u0440\u044b\u0442\u044c",
        "button_fix": "\u0418\u0441\u043f\u0440\u0430\u0432\u0438\u0442\u044c",
        "button_undo": "\u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c \u0432\u0441\u0451",
        "button_buy_pro": "\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c Pro",
        "button_consent": "\u042f \u0441\u043e\u0433\u043b\u0430\u0441\u0435\u043d",
        "button_privacy": "\u041f\u0440\u0438\u0432\u0430\u0442\u043d\u043e\u0441\u0442\u044c",
    },
    "pl": {
        "start_welcome": (
            "OneDrop zamienia wszystko, co tu wy\u015blesz, w uporz\u0105dkowane wpisy.\n\n"
            "Wy\u015blij zdanie, wiadomo\u015b\u0107 g\u0142osow\u0105 lub zdj\u0119cie jedzenia. Utworz\u0119 zadania, "
            "wydarzenia, wydatki, posi\u0142ki, nawyki i notatki."
        ),
        "onboarding_consent": (
            "Przed pierwszym zapytaniem AI potrzebuj\u0119 zgody na przetwarzanie tekstu, "
            "g\u0142osu i zdj\u0119\u0107. Dane mo\u017cesz w ka\u017cdej chwili wyeksportowa\u0107 lub usun\u0105\u0107."
        ),
        "onboarding_done": "Gotowe. Spr\u00f3buj: 'Jutro o 15:00 spotkanie z Andrzejem'.",
        "help": (
            "Komendy:\n"
            "/today - przegl\u0105d dnia\n"
            "/plan - zaplanuj dzie\u0144\n"
            "/settings - ustawienia i przypomnienia\n"
            "/help - ta wiadomo\u015b\u0107\n\n"
            "Wy\u015blij tekst, g\u0142os lub zdj\u0119cie jedzenia."
        ),
        "ack": "Przyj\u0105\u0142em, analizuj\u0119 wiadomo\u015b\u0107...",
        "today_header": "Dzisiaj",
        "today_empty": "Na razie pusto. Wy\u015blij co\u015b, a zapisz\u0119.",
        "plan_prompt": (
            "Co masz na g\u0142owie? Wy\u015blij w jednej wiadomo\u015bci: zadania, spotkania, "
            "wydatki. Rozdziel\u0119 to na wpisy."
        ),
        "settings_header": "Ustawienia",
        "settings_body": (
            "Strefa czasowa: {timezone}\nWaluta: {currency}\n"
            "Przypomnienia: {reminders}\nPlan: {plan}"
        ),
        "limit_left": "Pozosta\u0142o akcji AI: {remaining}",
        "limit_reached": (
            "Dzienny limit AI wyczerpany. Odnowi si\u0119 jutro albo w\u0142\u0105cz Pro."
        ),
        "paywall": (
            "Pro daje rozpoznawanie zdj\u0119\u0107 jedzenia, porann\u0105 zapowied\u017a, rozszerzon\u0105 "
            "analityk\u0119, eksport CSV i miesi\u0119czny limit AI za {price} Stars na {days} dni."
        ),
        "result_header": "Utworzono:",
        "result_empty": "Nie znalaz\u0142em nic do zapisania w tej wiadomo\u015bci.",
        "needs_confirmation": "Jedno pytanie przed zapisem: {question}",
        "undo_done": "Cofni\u0119te. Usuni\u0119to wpis\u00f3w: {count}.",
        "error_generic": "Coś posz\u0142o nie tak. Nic nie zapisano. Spr\u00f3buj ponownie.",
        "unsupported": "Obs\u0142uguj\u0119 tekst, wiadomo\u015bci g\u0142osowe i zdj\u0119cia.",
        "button_open": "Otw\u00f3rz",
        "button_fix": "Popraw",
        "button_undo": "Cofnij wszystko",
        "button_buy_pro": "W\u0142\u0105cz Pro",
        "button_consent": "Zgadzam si\u0119",
        "button_privacy": "Prywatno\u015b\u0107",
    },
    "uk": {
        "start_welcome": (
            "OneDrop \u043f\u0435\u0440\u0435\u0442\u0432\u043e\u0440\u044e\u0454 \u0432\u0441\u0435, \u0449\u043e \u0432\u0438 \u0441\u044e\u0434\u0438 \u043d\u0430\u0434\u0441\u0438\u043b\u0430\u0454\u0442\u0435, \u0443 "
            "\u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u043e\u0432\u0430\u043d\u0456 \u0437\u0430\u043f\u0438\u0441\u0438.\n\n"
            "\u041d\u0430\u0434\u0456\u0448\u043b\u0456\u0442\u044c \u0442\u0435\u043a\u0441\u0442, \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0435 \u043f\u043e\u0432\u0456\u0434\u043e\u043c\u043b\u0435\u043d\u043d\u044f \u0430\u0431\u043e \u0444\u043e\u0442\u043e \u0457\u0436\u0456."
        ),
        "onboarding_consent": (
            "\u041f\u0435\u0440\u0435\u0434 \u043f\u0435\u0440\u0448\u0438\u043c AI-\u0437\u0430\u043f\u0438\u0442\u043e\u043c \u043f\u043e\u0442\u0440\u0456\u0431\u043d\u0430 \u0432\u0430\u0448\u0430 \u0437\u0433\u043e\u0434\u0430 \u043d\u0430 "
            "\u043e\u0431\u0440\u043e\u0431\u043a\u0443 \u0442\u0435\u043a\u0441\u0442\u0443, \u0433\u043e\u043b\u043e\u0441\u0443 \u0442\u0430 \u0444\u043e\u0442\u043e."
        ),
        "onboarding_done": (
            "\u0413\u043e\u0442\u043e\u0432\u043e. \u0421\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435: \u00ab\u0417\u0430\u0432\u0442\u0440\u0430 \u043e 15:00 \u0437\u0443\u0441\u0442\u0440\u0456\u0447 \u0437 \u0410\u043d\u0434\u0440\u0456\u0454\u043c\u00bb."
        ),
        "help": (
            "\u041a\u043e\u043c\u0430\u043d\u0434\u0438:\n"
            "/today - \u043e\u0433\u043b\u044f\u0434 \u0434\u043d\u044f\n"
            "/plan - \u0441\u043f\u043b\u0430\u043d\u0443\u0432\u0430\u0442\u0438 \u0434\u0435\u043d\u044c\n"
            "/settings - \u043d\u0430\u043b\u0430\u0448\u0442\u0443\u0432\u0430\u043d\u043d\u044f\n"
            "/help - \u0446\u0435 \u043f\u043e\u0432\u0456\u0434\u043e\u043c\u043b\u0435\u043d\u043d\u044f"
        ),
        "ack": "\u041f\u0440\u0438\u0439\u043d\u044f\u0442\u043e, \u0440\u043e\u0437\u0431\u0438\u0440\u0430\u044e \u043f\u043e\u0432\u0456\u0434\u043e\u043c\u043b\u0435\u043d\u043d\u044f...",
        "today_header": "\u0421\u044c\u043e\u0433\u043e\u0434\u043d\u0456",
        "today_empty": (
            "\u041f\u043b\u0430\u043d\u0456\u0432 \u043f\u043e\u043a\u0438 \u043d\u0435\u043c\u0430\u0454. \u041d\u0430\u0434\u0456\u0448\u043b\u0456\u0442\u044c \u0449\u043e-\u043d\u0435\u0431\u0443\u0434\u044c."
        ),
        "plan_prompt": (
            "\u0429\u043e \u0432 \u043f\u043b\u0430\u043d\u0430\u0445? \u041d\u0430\u0434\u0456\u0448\u043b\u0456\u0442\u044c \u043e\u0434\u043d\u0438\u043c \u043f\u043e\u0432\u0456\u0434\u043e\u043c\u043b\u0435\u043d\u043d\u044f\u043c."
        ),
        "settings_header": "\u041d\u0430\u043b\u0430\u0448\u0442\u0443\u0432\u0430\u043d\u043d\u044f",
        "settings_body": (
            "\u0427\u0430\u0441\u043e\u0432\u0438\u0439 \u043f\u043e\u044f\u0441: {timezone}\n\u0412\u0430\u043b\u044e\u0442\u0430: {currency}\n"
            "\u041d\u0430\u0433\u0430\u0434\u0443\u0432\u0430\u043d\u043d\u044f: {reminders}\n\u0422\u0430\u0440\u0438\u0444: {plan}"
        ),
        "limit_left": "\u0417\u0430\u043b\u0438\u0448\u0438\u043b\u043e\u0441\u044f AI-\u0434\u0456\u0439: {remaining}",
        "limit_reached": (
            "\u0414\u0435\u043d\u043d\u0438\u0439 \u043b\u0456\u043c\u0456\u0442 AI \u0432\u0438\u0447\u0435\u0440\u043f\u0430\u043d\u043e. \u041e\u043d\u043e\u0432\u0438\u0442\u044c\u0441\u044f \u0437\u0430\u0432\u0442\u0440\u0430."
        ),
        "paywall": (
            "Pro \u0432\u0456\u0434\u043a\u0440\u0438\u0432\u0430\u0454 \u0440\u043e\u0437\u043f\u0456\u0437\u043d\u0430\u0432\u0430\u043d\u043d\u044f \u0444\u043e\u0442\u043e \u0457\u0436\u0456, \u0440\u0430\u043d\u043a\u043e\u0432\u0438\u0439 \u043e\u0433\u043b\u044f\u0434 "
            "\u0442\u0430 \u0435\u043a\u0441\u043f\u043e\u0440\u0442 CSV \u0437\u0430 {price} Stars \u043d\u0430 {days} \u0434\u043d\u0456\u0432."
        ),
        "result_header": "\u0421\u0442\u0432\u043e\u0440\u0435\u043d\u043e:",
        "result_empty": (
            "\u0423 \u0446\u044c\u043e\u043c\u0443 \u043f\u043e\u0432\u0456\u0434\u043e\u043c\u043b\u0435\u043d\u043d\u0456 \u043d\u0435 \u0437\u043d\u0430\u0439\u0448\u043b\u043e\u0441\u044f, \u0449\u043e \u0437\u0431\u0435\u0440\u0435\u0433\u0442\u0438."
        ),
        "needs_confirmation": "\u0423\u0442\u043e\u0447\u043d\u0456\u0442\u044c, \u0431\u0443\u0434\u044c \u043b\u0430\u0441\u043a\u0430: {question}",
        "undo_done": "\u0421\u043a\u0430\u0441\u043e\u0432\u0430\u043d\u043e. \u0412\u0438\u0434\u0430\u043b\u0435\u043d\u043e \u0437\u0430\u043f\u0438\u0441\u0456\u0432: {count}.",
        "error_generic": (
            "\u0429\u043e\u0441\u044c \u043f\u0456\u0448\u043b\u043e \u043d\u0435 \u0442\u0430\u043a. \u041d\u0456\u0447\u043e\u0433\u043e \u043d\u0435 \u0437\u0431\u0435\u0440\u0435\u0436\u0435\u043d\u043e."
        ),
        "unsupported": (
            "\u042f \u0440\u043e\u0437\u0443\u043c\u0456\u044e \u0442\u0435\u043a\u0441\u0442, \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0456 \u043f\u043e\u0432\u0456\u0434\u043e\u043c\u043b\u0435\u043d\u043d\u044f \u0442\u0430 \u0444\u043e\u0442\u043e."
        ),
        "button_open": "\u0412\u0456\u0434\u043a\u0440\u0438\u0442\u0438",
        "button_fix": "\u0412\u0438\u043f\u0440\u0430\u0432\u0438\u0442\u0438",
        "button_undo": "\u0421\u043a\u0430\u0441\u0443\u0432\u0430\u0442\u0438 \u0432\u0441\u0435",
        "button_buy_pro": "\u041f\u0456\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u0438 Pro",
        "button_consent": "\u042f \u0437\u0433\u043e\u0434\u0435\u043d",
        "button_privacy": "\u041f\u0440\u0438\u0432\u0430\u0442\u043d\u0456\u0441\u0442\u044c",
    },
}


def normalise_locale(locale: str | None) -> str:
    if not locale:
        return DEFAULT_LOCALE
    short = locale.split("-")[0].lower()
    return short if short in SUPPORTED_LOCALES else DEFAULT_LOCALE


def t(locale: str | None, key: str, **kwargs: Any) -> str:
    """Localized string with English fallback and safe formatting."""
    resolved = normalise_locale(locale)
    template = TEXTS.get(resolved, {}).get(key) or TEXTS[DEFAULT_LOCALE].get(key, key)
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
