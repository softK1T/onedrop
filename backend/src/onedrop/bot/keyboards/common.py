"""Inline keyboards. Callback data is short and always prefixed."""

from __future__ import annotations

from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from onedrop.bot.texts import t
from onedrop.config import get_settings

CALLBACK_FIX = "fix"
CALLBACK_UNDO = "undo"
CALLBACK_CONSENT = "consent"
CALLBACK_BUY_PRO = "buy_pro"


def _webapp_button(text: str, path: str = "") -> InlineKeyboardButton:
    base = get_settings().public_webapp_url.rstrip("/")
    return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=f"{base}/{path}".rstrip("/")))


def result_keyboard(locale: str | None, inbox_item_id: UUID) -> InlineKeyboardMarkup:
    """Open / Fix / Undo all, shown under a capture result."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_webapp_button(t(locale, "button_open"), f"inbox/{inbox_item_id}")],
            [
                InlineKeyboardButton(
                    text=t(locale, "button_fix"),
                    callback_data=f"{CALLBACK_FIX}:{inbox_item_id}",
                ),
                InlineKeyboardButton(
                    text=t(locale, "button_undo"),
                    callback_data=f"{CALLBACK_UNDO}:{inbox_item_id}",
                ),
            ],
        ]
    )


def consent_keyboard(locale: str | None) -> InlineKeyboardMarkup:
    """Onboarding consent plus a link to the privacy screen."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(locale, "button_consent"), callback_data=CALLBACK_CONSENT
                )
            ],
            [_webapp_button(t(locale, "button_privacy"), "privacy")],
        ]
    )


def paywall_keyboard(locale: str | None) -> InlineKeyboardMarkup:
    """Pro upgrade entry point."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(locale, "button_buy_pro"), callback_data=CALLBACK_BUY_PRO
                )
            ],
            [_webapp_button(t(locale, "button_open"), "subscription")],
        ]
    )


def open_app_keyboard(locale: str | None, path: str = "") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_webapp_button(t(locale, "button_open"), path)]]
    )
