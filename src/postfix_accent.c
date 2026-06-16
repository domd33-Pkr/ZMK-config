#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/logging/log.h>

#include <zmk/events/keycode_state_changed.h>
#include <zmk/event_manager.h>
#include <zmk/endpoints.h>
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
    zmk_hid_keyboard_press(keycode);
    zmk_endpoint_send_report(HID_USAGE_KEY);
    
    zmk_hid_keyboard_release(keycode);
    zmk_endpoint_send_report(HID_USAGE_KEY);
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

        // --- DÉTECTION DU SYMBOLE D'ACCENT ---
        
        // 1. Symbole '#' (Touche 3 + Shift) -> Utilisé pour é et ç
        if (keycode == HID_USAGE_KEY_KEYBOARD_3_AND_HASH) {
            is_accent_modifier = true;
            if (last_base_keycode == HID_USAGE_KEY_KEYBOARD_E) {
                replacement_keycode = HID_USAGE_KEY_KEYBOARD_SLASH_AND_QUESTION_MARK; // 'é' en Canadien Multilingue
            } else if (last_base_keycode == HID_USAGE_KEY_KEYBOARD_C) {
                replacement_keycode = HID_USAGE_KEY_KEYBOARD_RIGHT_BRACKET_AND_RIGHT_BRACE; // 'ç' en Canadien Multilingue
            }
        }
        // 2. Symbole '$' (Touche 4 + Shift) -> Utilisé pour ^ (circonflexe)
        else if (keycode == HID_USAGE_KEY_KEYBOARD_4_AND_DOLLAR) {
            is_accent_modifier = true;
            // Touche morte '[' en Canadien Multilingue
            dead_key = HID_USAGE_KEY_KEYBOARD_LEFT_BRACKET_AND_LEFT_BRACE;
        }
        // 3. Symbole '%' (Touche 5 + Shift) -> Utilisé pour ` (grave)
        else if (keycode == HID_USAGE_KEY_KEYBOARD_5_AND_PERCENT) {
            is_accent_modifier = true;
            if (last_base_keycode == HID_USAGE_KEY_KEYBOARD_E) {
                replacement_keycode = HID_USAGE_KEY_KEYBOARD_APOSTROPHE_AND_QUOTE; // 'è' en Canadien
            } else if (last_base_keycode == HID_USAGE_KEY_KEYBOARD_A) {
                replacement_keycode = HID_USAGE_KEY_KEYBOARD_BACKSLASH_AND_PIPE; // 'à' en Canadien
            } else if (last_base_keycode == HID_USAGE_KEY_KEYBOARD_U) {
                // 'ù' en Canadien est souvent 'AltGr + \' ou une touche morte complexe.
                // Pour faire simple et robuste, on utilise la touche morte de l'accent grave
                // qui est AltGr + '[' ou 'Shift + \' selon les variantes.
                // Si l'utilisateur n'en a pas besoin, on laisse tel quel. On va mapper à AltGr + \ pour le ù.
                // Comme ZMK ne gère pas AltGr facilement ici, on va ignorer le 'ù' direct ou envoyer une combinaison.
            }
        }
        // 4. Symbole '~' (Shift + ` / Touche Grave/Tilde) -> Utilisé pour ¨ (tréma)
        else if (keycode == HID_USAGE_KEY_KEYBOARD_GRAVE_ACCENT_AND_TILDE) {
            is_accent_modifier = true;
            // Touche morte Shift + '[' en Canadien Multilingue
            dead_key = HID_USAGE_KEY_KEYBOARD_LEFT_BRACKET_AND_LEFT_BRACE;
            dead_key_shift = true;
        }

        if (is_accent_modifier) {
            k_work_cancel_delayable(&accent_timeout_work);
            waiting_for_accent = false;

            // Efface la lettre précédente (ex: 'e')
            inject_keycode(HID_USAGE_KEY_KEYBOARD_DELETE_BACKSPACE);

            if (replacement_keycode != 0) {
                // Injecte la lettre accentuée directe (é, è, ç, à)
                inject_keycode(replacement_keycode);
            } else if (dead_key != 0) {
                // Injecte la touche morte (ex: ^ ou ¨)
                if (dead_key_shift) {
                    zmk_hid_keyboard_press(HID_USAGE_KEY_KEYBOARD_LEFTSHIFT);
                }
                zmk_hid_keyboard_press(dead_key);
                zmk_endpoint_send_report(HID_USAGE_KEY);
                
                zmk_hid_keyboard_release(dead_key);
                if (dead_key_shift) {
                    zmk_hid_keyboard_release(HID_USAGE_KEY_KEYBOARD_LEFTSHIFT);
                }
                zmk_endpoint_send_report(HID_USAGE_KEY);
                
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
