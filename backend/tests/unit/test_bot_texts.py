"""Bot copy: locale parity and safe formatting."""

from __future__ import annotations

from onedrop.bot.texts import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    TEXTS,
    normalise_locale,
    t,
)


def test_every_supported_locale_has_a_table() -> None:
    assert set(TEXTS) == set(SUPPORTED_LOCALES)


def test_all_locales_share_the_same_keys() -> None:
    reference = set(TEXTS[DEFAULT_LOCALE])
    for locale in SUPPORTED_LOCALES:
        assert set(TEXTS[locale]) == reference, locale


def test_no_string_is_empty() -> None:
    for locale, table in TEXTS.items():
        for key, value in table.items():
            assert value.strip(), f"{locale}:{key}"


def test_locale_is_normalised_with_fallback() -> None:
    assert normalise_locale("ru-RU") == "ru"
    assert normalise_locale("PL") == "pl"
    assert normalise_locale("de") == DEFAULT_LOCALE
    assert normalise_locale(None) == DEFAULT_LOCALE


def test_placeholders_are_filled() -> None:
    assert "7" in t("ru", "limit_left", remaining=7)
    assert "250" in t("en", "paywall", price=250, days=30)


def test_missing_placeholder_does_not_raise() -> None:
    assert t("en", "limit_left") == TEXTS["en"]["limit_left"]


def test_unknown_key_returns_the_key() -> None:
    assert t("en", "does_not_exist") == "does_not_exist"


def test_ack_matches_the_specified_behaviour() -> None:
    assert "\u0440\u0430\u0437\u0431\u0438\u0440\u0430\u044e" in t("ru", "ack")
    assert "parsing" in t("en", "ack")
