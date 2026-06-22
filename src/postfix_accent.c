#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/logging/log.h>

#include <zmk/events/keycode_state_changed.h>
#include <zmk/event_manager.h>
#include <zmk/hid.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

// État de la machine
static bool waiting_for_accent = false;
static uint16_t last_base_keycode = 0;
static struct k_work_delayable accent_timeout_work;

static void accent_timeout_handler(struct k_work *work) {
    waiting_for_accent = false;
    last_base_keycode = 0;
    LOG_DBG("Postfix accent timeout expired");
}

// Fonction pour injecter rapidement une touche
static void inject_keycode(uint16_t keycode) {
    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, keycode), true, k_uptime_get());
    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, keycode), false, k_uptime_get());
}

int postfix_accent_listener(const zmk_event_t *eh) {
    const struct zmk_keycode_state_changed *ev = as_zmk_keycode_state_changed(eh);
    if (ev == NULL) {
        return ZMK_EV_EVENT_BUBBLE;
    }

    if (!ev->state) { 
        // On ignore les relâchements de touche
        return ZMK_EV_EVENT_BUBBLE;
    }

    uint16_t keycode = ev->keycode;

    // Ignore les modificateurs eux-mêmes pour ne pas annuler l'attente
    if (keycode >= HID_USAGE_KEY_KEYBOARD_LEFTCONTROL && keycode <= HID_USAGE_KEY_KEYBOARD_RIGHT_GUI) {
        return ZMK_EV_EVENT_BUBBLE;
    }

    if (waiting_for_accent) {
        bool is_accent_modifier = false;
        uint16_t replacement_keycode = 0;
        uint16_t dead_key = 0;
        bool dead_key_shift = false;
        bool is_cedilla = false;

        // --- DÉTECTION DU SYMBOLE D'ACCENT ---
        
        // 1. Symbole '#' (Touche 3 + Shift) -> Utilisé pour é et ç
        // Sous US International, la touche morte pour l'accent aigu est l'apostrophe (')
        if (keycode == HID_USAGE_KEY_KEYBOARD_3_AND_HASH) {
            is_accent_modifier = true;
            if (last_base_keycode == HID_USAGE_KEY_KEYBOARD_C) {
                is_cedilla = true;
            } else {
                dead_key = HID_USAGE_KEY_KEYBOARD_APOSTROPHE_AND_QUOTE;
            }
        }
        // 2. Symbole '$' (Touche 4 + Shift) -> Utilisé pour ^ (circonflexe)
        // Sous US International, la touche morte pour le circonflexe est Shift + 6 (^)
        else if (keycode == HID_USAGE_KEY_KEYBOARD_4_AND_DOLLAR) {
            is_accent_modifier = true;
            dead_key = HID_USAGE_KEY_KEYBOARD_6_AND_CARET;
            dead_key_shift = true;
        }
        // 3. Symbole '%' (Touche 5 + Shift) -> Utilisé pour ` (grave)
        // Sous US International, la touche morte pour l'accent grave est le backtick (`)
        else if (keycode == HID_USAGE_KEY_KEYBOARD_5_AND_PERCENT) {
            is_accent_modifier = true;
            dead_key = HID_USAGE_KEY_KEYBOARD_GRAVE_ACCENT_AND_TILDE;
        }
        // 4. Symbole '~' (Shift + ` / Touche Grave/Tilde) -> Utilisé pour ¨ (tréma)
        // Sous US International, la touche morte pour le tréma est Shift + ' (")
        else if (keycode == HID_USAGE_KEY_KEYBOARD_GRAVE_ACCENT_AND_TILDE) {
            is_accent_modifier = true;
            dead_key = HID_USAGE_KEY_KEYBOARD_APOSTROPHE_AND_QUOTE;
            dead_key_shift = true;
        }

        if (is_accent_modifier) {
            k_work_cancel_delayable(&accent_timeout_work);
            waiting_for_accent = false;

            // Efface la lettre précédente (ex: 'e')
            inject_keycode(HID_USAGE_KEY_KEYBOARD_DELETE_BACKSPACE);

            if (is_cedilla) {
                // Injecte AltGr + ',' pour faire 'ç' sous Linux en US International
                raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_RIGHTALT), true, k_uptime_get());
                inject_keycode(HID_USAGE_KEY_KEYBOARD_COMMA_AND_LESS_THAN);
                raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_RIGHTALT), false, k_uptime_get());
            } else if (replacement_keycode != 0) {
                // Injecte la lettre accentuée directe (é, è, ç, à)
                inject_keycode(replacement_keycode);
            } else if (dead_key != 0) {
                // Injecte la touche morte (ex: ^ ou ¨)
                if (dead_key_shift) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), true, k_uptime_get());
                }
                raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, dead_key), true, k_uptime_get());
                
                raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, dead_key), false, k_uptime_get());
                if (dead_key_shift) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), false, k_uptime_get());
                }
                
                // Ensuite injecte la lettre de base (ex: 'e')
                inject_keycode(last_base_keycode);
            }
            
            // On bloque la touche '#' (ou autre) pour qu'elle ne s'affiche pas
            return ZMK_EV_EVENT_HANDLED;
        } else {
            // Une autre touche normale a été tapée, on annule l'attente et on la laisse passer
            k_work_cancel_delayable(&accent_timeout_work);
            waiting_for_accent = false;
        }
    }

    // --- DÉTECTION DES LETTRES DE BASE ---
    if (keycode == HID_USAGE_KEY_KEYBOARD_A ||
        keycode == HID_USAGE_KEY_KEYBOARD_E ||
        keycode == HID_USAGE_KEY_KEYBOARD_I ||
        keycode == HID_USAGE_KEY_KEYBOARD_O ||
        keycode == HID_USAGE_KEY_KEYBOARD_U ||
        keycode == HID_USAGE_KEY_KEYBOARD_C) {
        
        last_base_keycode = keycode;
        waiting_for_accent = true;
        
        // Lance ou relance le timer de 2000 ms (2 secondes)
        k_work_reschedule(&accent_timeout_work, K_MSEC(2000));
    }

    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(postfix_accent, postfix_accent_listener);
ZMK_SUBSCRIPTION(postfix_accent, zmk_keycode_state_changed);

static int postfix_accent_init(void) {
    k_work_init_delayable(&accent_timeout_work, accent_timeout_handler);
    return 0;
}

SYS_INIT(postfix_accent_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
