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
static bool left_shift_held = false;
static bool right_shift_held = false;
static bool last_base_was_shifted = false;
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

    uint16_t keycode = ev->keycode;

    // Suivi de l'état des touches Shift physiques ou logiques
    if (keycode == HID_USAGE_KEY_KEYBOARD_LEFTSHIFT) {
        left_shift_held = ev->state;
        return ZMK_EV_EVENT_BUBBLE;
    }
    if (keycode == HID_USAGE_KEY_KEYBOARD_RIGHTSHIFT) {
        right_shift_held = ev->state;
        return ZMK_EV_EVENT_BUBBLE;
    }

    if (!ev->state) { 
        // On ignore les relâchements de touche pour le reste du traitement
        return ZMK_EV_EVENT_BUBBLE;
    }

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
        if (keycode == HID_USAGE_KEY_KEYBOARD_3_AND_HASH) {
            is_accent_modifier = true;
            if (last_base_keycode == HID_USAGE_KEY_KEYBOARD_C) {
                is_cedilla = true;
            } else {
                dead_key = HID_USAGE_KEY_KEYBOARD_APOSTROPHE_AND_QUOTE;
            }
        }
        // 2. Touche '$' (Touche 4 + Shift) -> Utilisé pour ^ (circonflexe)
        else if (keycode == HID_USAGE_KEY_KEYBOARD_4_AND_DOLLAR) {
            is_accent_modifier = true;
            dead_key = HID_USAGE_KEY_KEYBOARD_6_AND_CARET;
            dead_key_shift = true;
        }
        // 3. Touche '%' (Touche 5 + Shift) -> Utilisé pour ` (grave)
        else if (keycode == HID_USAGE_KEY_KEYBOARD_5_AND_PERCENT) {
            is_accent_modifier = true;
            dead_key = HID_USAGE_KEY_KEYBOARD_GRAVE_ACCENT_AND_TILDE;
        }
        // 4. Symbole '~' (Shift + ` / Touche Grave/Tilde) -> Utilisé pour ¨ (tréma)
        else if (keycode == HID_USAGE_KEY_KEYBOARD_GRAVE_ACCENT_AND_TILDE) {
            is_accent_modifier = true;
            dead_key = HID_USAGE_KEY_KEYBOARD_APOSTROPHE_AND_QUOTE;
            dead_key_shift = true;
        }

        if (is_accent_modifier) {
            k_work_cancel_delayable(&accent_timeout_work);
            waiting_for_accent = false;

            // Sauvegarde de l'état actuel des modificateurs de Shift physiques/actifs
            bool is_left_shift_active = left_shift_held;
            bool is_right_shift_active = right_shift_held;

            bool is_shift_active = is_left_shift_active || is_right_shift_active;

            // Set active shift state to match what the dead key needs (dead_key_shift)
            if (is_shift_active && !dead_key_shift) {
                if (is_left_shift_active) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), false, k_uptime_get());
                }
                if (is_right_shift_active) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_RIGHTSHIFT), false, k_uptime_get());
                }
            } else if (!is_shift_active && dead_key_shift) {
                raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), true, k_uptime_get());
            }

            // Delete the previous letter (e.g. 'e')
            inject_keycode(HID_USAGE_KEY_KEYBOARD_DELETE_BACKSPACE);

            if (is_cedilla) {
                // AltGr + ',' produces 'ç' under US International. Shift + AltGr + ',' produces 'Ç'.
                if (is_shift_active && !last_base_was_shifted) {
                    if (is_left_shift_active) {
                        raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), false, k_uptime_get());
                    }
                    if (is_right_shift_active) {
                        raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_RIGHTSHIFT), false, k_uptime_get());
                    }
                } else if (!is_shift_active && last_base_was_shifted) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), true, k_uptime_get());
                }

                raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_RIGHTALT), true, k_uptime_get());
                inject_keycode(HID_USAGE_KEY_KEYBOARD_COMMA_AND_LESS_THAN);
                raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_RIGHTALT), false, k_uptime_get());

                // Restore Shift state for cedilla
                if (is_shift_active && !last_base_was_shifted) {
                    if (is_left_shift_active) {
                        raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), true, k_uptime_get());
                    }
                    if (is_right_shift_active) {
                        raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_RIGHTSHIFT), true, k_uptime_get());
                    }
                } else if (!is_shift_active && last_base_was_shifted) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), false, k_uptime_get());
                }
            } else if (replacement_keycode != 0) {
                if (last_base_was_shifted) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), true, k_uptime_get());
                }
                inject_keycode(replacement_keycode);
                if (last_base_was_shifted) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), false, k_uptime_get());
                }
            } else if (dead_key != 0) {
                // Inject dead key
                inject_keycode(dead_key);
                
                // Adjust Shift for the base letter (e.g. 'e')
                bool current_shift_state = dead_key_shift;
                if (current_shift_state && !last_base_was_shifted) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), false, k_uptime_get());
                } else if (!current_shift_state && last_base_was_shifted) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), true, k_uptime_get());
                }

                // Inject base letter
                inject_keycode(last_base_keycode);

                // Restore Shift state post base-letter
                if (current_shift_state && !last_base_was_shifted) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), true, k_uptime_get());
                } else if (!current_shift_state && last_base_was_shifted) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), false, k_uptime_get());
                }
            }

            // Finally, restore the initial physical Shift state if it was altered
            if (is_shift_active && !dead_key_shift) {
                if (is_left_shift_active) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), true, k_uptime_get());
                }
                if (is_right_shift_active) {
                    raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_RIGHTSHIFT), true, k_uptime_get());
                }
            } else if (!is_shift_active && dead_key_shift) {
                raise_zmk_keycode_state_changed_from_encoded(ZMK_HID_USAGE(HID_USAGE_KEY, HID_USAGE_KEY_KEYBOARD_LEFTSHIFT), false, k_uptime_get());
            }
            
            // On bloque la touche de déclenchement d'accent pour qu'elle ne s'affiche pas
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
        last_base_was_shifted = (left_shift_held || right_shift_held);
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
