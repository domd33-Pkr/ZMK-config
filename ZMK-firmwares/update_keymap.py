#!/usr/bin/env python3
import json
import os
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.abspath(os.path.join(script_dir, "../../Key Configurator/Archives/keyboard_layout_updated.json"))
keymap_path = os.path.abspath(os.path.join(script_dir, "../boards/shields/optimized_fitness/optimized_fitness.keymap"))

def generate_keymap():
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}")
        exit(1)

    with open(json_path, 'r') as f:
        data = json.load(f)

    keys_by_index = { k["index"]: k for k in data.get("keys", []) }
    layer_mapping = data.get("layerMapping", [f"layer_{i}" for i in range(16)])
    layer_id_to_index = {nid: str(idx) for idx, nid in enumerate(layer_mapping)}

    def clean_keycode(code):
        code = code.upper().strip()
        aliases = {
            "'": "SQT",
            ",": "COMMA",
            ".": "DOT",
            "-": "MINUS",
            "_": "UNDER",
            "=": "EQUAL",
            "+": "PLUS",
            "[": "LBKT",
            "]": "RBKT",
            "\\": "BSLH",
            ";": "SEMI",
            "/": "FSLH",
            "`": "GRAVE",
            "SPACE": "SPC",
            "ENTER": "RET",
            "BKS": "BSPC",
            "EACUTE": "FSLH"
        }
        
        # Check for nested modifier format, e.g., LS(key) or RSFT(key)
        match = re.match(r'^([A-ZFTL_]+)\((.+)\)$', code)
        if match:
            mod = match.group(1)
            inner = match.group(2)
            mod_aliases = {
                'RSHIFT': 'RS', 'LSFT': 'LS', 'LSHIFT': 'LS', 'RSFT': 'RS',
                'RCTRL': 'RC', 'LCTRL': 'LC', 'LCTL': 'LC', 'RCTL': 'RC',
                'LALT': 'LA', 'RALT': 'RA', 'LGUI': 'LG', 'RGUI': 'RG'
            }
            if mod in mod_aliases:
                mod = mod_aliases[mod]
            return f"{mod}({clean_keycode(inner)})"
            
        if code in aliases:
            return aliases[code]
        return code

    def pad(text, width=27):
        return text.ljust(width)

    def format_binding(tap):
        if not tap:
            return "&trans"
        
        # Translate named layer ID references to physical layer numbers
        for nid, p_idx in layer_id_to_index.items():
            tap = re.sub(r'\b' + re.escape(nid) + r'\b', p_idx, tap)
            
        # Force uppercase and clean behavior parameters to avoid devicetree parse errors
        if tap.startswith("&kp "):
            tap = "&kp " + clean_keycode(tap[4:])
        elif tap.startswith("&mt "):
            parts = tap.split(None, 2)
            if len(parts) >= 3:
                tap = f"{parts[0]} {clean_keycode(parts[1])} {clean_keycode(parts[2])}"
        elif tap.startswith("&lt "):
            parts = tap.split(None, 2)
            if len(parts) >= 3:
                tap = f"{parts[0]} {parts[1]} {clean_keycode(parts[2])}"
        elif tap.startswith("&ht "):
            parts = tap.split(None, 2)
            if len(parts) >= 3:
                hold_key = clean_keycode(parts[1])
                tap_key = clean_keycode(parts[2])

                if (hold_key, tap_key) in [("DELTA", "DEGREE"), ("DELTA", "RA(LS(SEMI))"), ("DELTA", "RA(NUBS)")]:
                    return "&ht_delta_deg 0 0"
                if (hold_key, tap_key) in [("DEGREE", "DELTA"), ("RA(LS(SEMI))", "DELTA"), ("RA(NUBS)", "DELTA")]:
                    return "&ht_deg_delta 0 0"
                if (hold_key, tap_key) == ("PI", "OHM"):
                    return "&ht_pi_ohm 0 0"
                if (hold_key, tap_key) == ("OHM", "PI"):
                    return "&ht_ohm_pi 0 0"

                accent_map = {
                    "AGRAVE": "agrave",
                    "ACIRC": "acirc",
                    "EGRAVE": "egrave",
                    "ECIRC": "ecirc",
                    "CCEDIL": "ccedilla",
                    "UGRAVE": "ugrave",
                    "UCIRC": "ucirc",
                    "OCIRC": "ocirc",
                    "ICIRC": "icirc",
                    "ITREMA": "itrema",
                    "UTREMA": "utrema",
                    "ETREMA": "etrema",
                }

                if hold_key in accent_map and tap_key in accent_map:
                    if hold_key == "ETREMA" and tap_key == "EGRAVE":
                        return "&ht_etrema_egrave 0 0"
                    if hold_key == "ECIRC" and tap_key == "EGRAVE":
                        return "&ht_ecirc_egrave 0 0"
                    return f"&ht_{accent_map[hold_key]}_{accent_map[tap_key]} 0 0"

                if hold_key in accent_map:
                    return f"&ht_{accent_map[hold_key]}_kp 0 {tap_key}"

                if tap_key in accent_map:
                    return f"&ht_kp_{accent_map[tap_key]} {hold_key} 0"

                return f"&ht {hold_key} {tap_key}"

        if tap in ("&kp OHM", "OHM"):
            return "&uc_ohm"
        if tap in ("&kp DELTA", "DELTA"):
            return "&uc_delta"
        if tap in ("&kp PI", "PI"):
            return "&uc_pi"
        if tap in ("&kp DEGREE", "DEGREE"):
            return "&uc_deg"
        if tap in ("&kp CARET", "CARET", "&single_caret", "single_caret"):
            return "&single_caret"
        if tap in ("&kp LS(GRAVE)", "LS(GRAVE)"):
            return "&single_tilde"

        if tap in ("&kp AGRAVE", "AGRAVE", "&mm_agrave", "mm_agrave"):
            return "&mm_agrave"
        if tap in ("&kp ACIRC", "ACIRC", "&kp ACIRCUMFLEX", "ACIRCUMFLEX", "&mm_acirc", "mm_acirc"):
            return "&mm_acirc"
        if tap in ("&kp EGRAVE", "EGRAVE", "&mm_egrave", "mm_egrave"):
            return "&mm_egrave"
        if tap in ("&kp CCEDIL", "CCEDIL", "&mm_ccedilla", "mm_ccedilla"):
            return "&mm_ccedilla"
        if tap in ("&kp UGRAVE", "UGRAVE", "&mm_ugrave", "mm_ugrave"):
            return "&mm_ugrave"
        if tap in ("&kp OCIRC", "OCIRC", "&kp OCIRCUMFLEX", "OCIRCUMFLEX", "&mm_ocirc", "mm_ocirc"):
            return "&mm_ocirc"
        if tap in ("&kp ICIRC", "ICIRC", "&kp ICIRCUMFLEX", "ICIRCUMFLEX", "&mm_icirc", "mm_icirc"):
            return "&mm_icirc"
        if tap in ("&kp ECIRC", "ECIRC", "&kp ECIRCUMFLEX", "ECIRCUMFLEX", "&mm_ecirc", "mm_ecirc"):
            return "&mm_ecirc"
        if tap in ("&kp UCIRC", "UCIRC", "&kp UCIRCUMFLEX", "UCIRCUMFLEX", "&mm_ucirc", "mm_ucirc"):
            return "&mm_ucirc"
        if tap in ("&kp ITREMA", "ITREMA", "&kp IDIER", "IDIER", "&kp IDIAER", "IDIAER", "&mm_itrema", "mm_itrema", "&mm_idier", "mm_idier"):
            return "&mm_itrema"
        if tap in ("&kp UTREMA", "UTREMA", "&kp UDIER", "UDIER", "&kp UDIAER", "UDIAER", "&mm_utrema", "mm_utrema", "&mm_udier", "mm_udier"):
            return "&mm_utrema"
        if tap in ("&kp ETREMA", "ETREMA", "&kp EDIER", "EDIER", "&kp EDIAER", "EDIAER", "&mm_etrema", "mm_etrema", "&mm_edier", "mm_edier"):
            return "&mm_etrema"
        if tap in ("&kp EACUTE", "EACUTE"):
            return "&kp FSLH"
        
        tap = tap.replace("RSHIFT(", "RS(").replace("LSHIFT(", "LS(")
        tap = tap.replace("RCTRL(", "RC(").replace("LCTRL(", "LC(")
        tap = tap.replace("RCTL(", "RC(").replace("LCTL(", "LC(")
        tap = tap.replace("RALT(", "RA(").replace("LALT(", "LA(")
        tap = tap.replace("RGUI(", "RG(").replace("LGUI(", "LG(")
        
        tap = tap.replace(" ENTER", " RET").replace("(ENTER)", "(RET)")
        tap = tap.replace(" SPACE", " SPC").replace("(SPACE)", "(SPC)")
        tap = tap.replace(" BKS", " BSPC").replace("(BKS)", "(BSPC)")
        tap = tap.replace("RGUI(", "RG(").replace("LGUI(", "LG(")
        
        if not tap.startswith("&") and tap != "":
            tap = clean_keycode(tap)
            tap = f"&kp {tap}"
            
        return tap

    new_keymap = []
    new_keymap.append('    keymap {')
    new_keymap.append('        compatible = "zmk,keymap";\n')

    for layer in range(16):
        named_layer_id = layer_mapping[layer] if layer < len(layer_mapping) else f"layer_{layer}"
        new_keymap.append(f'        layer_{layer + 1} {{')
        new_keymap.append('            bindings = <')
        new_keymap.append('                // Left hand (Index 1 to 10)')
        
        for i in range(1, 11):
            binding = "&trans"
            if i in keys_by_index:
                b = keys_by_index[i].get("bindings", {}).get(named_layer_id, {})
                tap = b.get("tap", "").strip()
                binding = format_binding(tap)
            new_keymap.append(f'                {pad(binding)}// {i}')
            
        new_keymap.append('')
        new_keymap.append('                // Right hand (Index 11 to 20)')
        for i in range(11, 21):
            binding = "&trans"
            if i in keys_by_index:
                b = keys_by_index[i].get("bindings", {}).get(named_layer_id, {})
                tap = b.get("tap", "").strip()
                binding = format_binding(tap)
            new_keymap.append(f'                {pad(binding)}// {i}')
            
        new_keymap.append('            >;')
        new_keymap.append('        };')
        new_keymap.append('')

    new_keymap.append('    };')
    new_keymap.append('};')

    timings = data.get("timings", {})
    ht_timing = timings.get("holdTap", {})
    mtl_timing = timings.get("moTapLayer", {})
    sticky_timing = timings.get("sticky", {})
    macro_timing = timings.get("macro", {})

    ht_term = int(ht_timing.get("tappingTermMs", 200))
    ht_flavor = ht_timing.get("flavor", "tap-preferred")
    ht_quick_tap = int(ht_timing.get("quickTapMs", 0))
    ht_idle = int(ht_timing.get("requirePriorIdleMs", 0))

    mtl_term = int(mtl_timing.get("tappingTermMs", 200))
    mtl_flavor = mtl_timing.get("flavor", "hold-preferred")

    sticky_release = int(sticky_timing.get("releaseAfterMs", 1000))
    sticky_quick = bool(sticky_timing.get("quickRelease", False))

    macro_tap = int(macro_timing.get("tapMs", 1))
    macro_wait = int(macro_timing.get("waitMs", 1))

    ht_extra = ""
    if ht_quick_tap > 0:
        ht_extra += f"\n            quick-tap-ms = <{ht_quick_tap}>;"
    if ht_idle > 0:
        ht_extra += f"\n            require-prior-idle-ms = <{ht_idle}>;"

    sticky_quick_str = "\n            quick-release;" if sticky_quick else ""

    top_part = f"""#include <behaviors.dtsi>
#include <dt-bindings/zmk/keys.h>
#include <dt-bindings/zmk/bt.h>
#include <dt-bindings/zmk/outputs.h>
#include <dt-bindings/zmk/modifiers.h>

#define DEGREE RA(NUBS)
#define EACUTE FSLH

/ {{
    behaviors {{
        ht: hold_tap {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&kp &kp>;
        }};

        ht_delta_deg: ht_delta_deg {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&uc_delta &deg>;
        }};

        ht_deg_delta: ht_deg_delta {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&deg &uc_delta>;
        }};

        ht_pi_ohm: ht_pi_ohm {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&uc_pi &uc_ohm>;
        }};

        ht_ohm_pi: ht_ohm_pi {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&uc_ohm &uc_pi>;
        }};

        ht_agrave_kp: ht_agrave_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_agrave &kp>;
        }};

        ht_acirc_kp: ht_acirc_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_acirc &kp>;
        }};

        ht_egrave_kp: ht_egrave_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_egrave &kp>;
        }};

        ht_ecirc_kp: ht_ecirc_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_ecirc &kp>;
        }};

        ht_ccedilla_kp: ht_ccedilla_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_ccedilla &kp>;
        }};

        ht_ugrave_kp: ht_ugrave_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_ugrave &kp>;
        }};

        ht_ucirc_kp: ht_ucirc_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_ucirc &kp>;
        }};

        ht_ocirc_kp: ht_ocirc_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_ocirc &kp>;
        }};

        ht_icirc_kp: ht_icirc_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_icirc &kp>;
        }};

        ht_itrema_kp: ht_itrema_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_itrema &kp>;
        }};

        ht_utrema_kp: ht_utrema_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_utrema &kp>;
        }};

        ht_etrema_kp: ht_etrema_kp {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_etrema &kp>;
        }};

        ht_etrema_egrave: ht_etrema_egrave {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_etrema &mm_egrave>;
        }};

        ht_ecirc_egrave: ht_ecirc_egrave {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{ht_flavor}";
            tapping-term-ms = <{ht_term}>;{ht_extra}
            bindings = <&mm_ecirc &mm_egrave>;
        }};

        mm_agrave: mod_morph_agrave {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_agrave>, <&macro_agrave_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mm_acirc: mod_morph_acirc {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_acirc>, <&macro_acirc_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mm_egrave: mod_morph_egrave {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_egrave>, <&macro_egrave_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mm_ccedilla: mod_morph_ccedilla {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_ccedilla>, <&macro_ccedilla_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mm_ugrave: mod_morph_ugrave {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_ugrave>, <&macro_ugrave_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mm_ocirc: mod_morph_ocirc {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_ocirc>, <&macro_ocirc_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mm_icirc: mod_morph_icirc {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_icirc>, <&macro_icirc_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mm_ecirc: mod_morph_ecirc {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_ecirc>, <&macro_ecirc_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mm_ucirc: mod_morph_ucirc {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_ucirc>, <&macro_ucirc_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mm_itrema: mod_morph_itrema {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_itrema>, <&macro_itrema_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mm_utrema: mod_morph_utrema {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_utrema>, <&macro_utrema_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mm_etrema: mod_morph_etrema {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_etrema>, <&macro_etrema_maj>;
            mods = <(MOD_LSFT|MOD_RSFT)>;
        }};

        mtl: mo_tap_layer {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{mtl_flavor}";
            tapping-term-ms = <{mtl_term}>;
            bindings = <&mo &sl>;
        }};

        sk: sticky_key {{
            compatible = "zmk,behavior-sticky-key";
            #binding-cells = <1>;
            bindings = <&kp>;
            release-after-ms = <{sticky_release}>;{sticky_quick_str}
        }};

        sl: sticky_layer {{
            compatible = "zmk,behavior-sticky-key";
            #binding-cells = <1>;
            bindings = <&mo>;
            release-after-ms = <{sticky_release}>;{sticky_quick_str}
        }};
    }};

    macros {{
        deg: deg {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            tap-ms = <{macro_tap}>;
            wait-ms = <{macro_wait}>;
            bindings = <&macro_press &kp LCTRL &kp LSHFT>
                     , <&macro_tap &kp U>
                     , <&macro_release &kp LCTRL &kp LSHFT>
                     , <&macro_tap &kp NUMBER_0 &kp NUMBER_0 &kp B &kp NUMBER_0 &kp RET>;
        }};

        uc_deg: uc_deg {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            tap-ms = <{macro_tap}>;
            wait-ms = <{macro_wait}>;
            bindings = <&macro_press &kp LCTRL &kp LSHFT>
                     , <&macro_tap &kp U>
                     , <&macro_release &kp LCTRL &kp LSHFT>
                     , <&macro_tap &kp NUMBER_0 &kp NUMBER_0 &kp B &kp NUMBER_0 &kp RET>;
        }};

        single_tilde: single_tilde {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            bindings = <&macro_tap &kp LS(GRAVE) &kp SPACE>;
        }};

        single_caret: single_caret {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LBKT &kp SPACE>;
        }};

        macro_agrave: macro_agrave {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp SQT &kp A>;
        }};

        macro_agrave_maj: macro_agrave_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp SQT &kp LS(A)>;
        }};

        macro_egrave: macro_egrave {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp SQT &kp E>;
        }};

        macro_egrave_maj: macro_egrave_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp SQT &kp LS(E)>;
        }};

        macro_ccedilla: macro_ccedilla {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp RBKT &kp C>;
        }};

        macro_ccedilla_maj: macro_ccedilla_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp RBKT &kp LS(C)>;
        }};

        macro_ugrave: macro_ugrave {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp SQT &kp U>;
        }};

        macro_ugrave_maj: macro_ugrave_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp SQT &kp LS(U)>;
        }};

        macro_acirc: macro_acirc {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LBKT &kp A>;
        }};

        macro_acirc_maj: macro_acirc_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LBKT &kp LS(A)>;
        }};

        macro_ocirc: macro_ocirc {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LBKT &kp O>;
        }};

        macro_ocirc_maj: macro_ocirc_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LBKT &kp LS(O)>;
        }};

        macro_icirc: macro_icirc {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LBKT &kp I>;
        }};

        macro_icirc_maj: macro_icirc_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LBKT &kp LS(I)>;
        }};

        macro_ecirc: macro_ecirc {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LBKT &kp E>;
        }};

        macro_ecirc_maj: macro_ecirc_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LBKT &kp LS(E)>;
        }};

        macro_ucirc: macro_ucirc {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LBKT &kp U>;
        }};

        macro_ucirc_maj: macro_ucirc_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LBKT &kp LS(U)>;
        }};

        macro_itrema: macro_itrema {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LS(RBKT) &kp I>;
        }};

        macro_itrema_maj: macro_itrema_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LS(RBKT) &kp LS(I)>;
        }};

        macro_utrema: macro_utrema {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LS(RBKT) &kp U>;
        }};

        macro_utrema_maj: macro_utrema_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LS(RBKT) &kp LS(U)>;
        }};

        macro_etrema: macro_etrema {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LS(RBKT) &kp E>;
        }};

        macro_etrema_maj: macro_etrema_maj {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = <&macro_tap &kp LS(RBKT) &kp LS(E)>;
        }};

        uc_delta: uc_delta {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            tap-ms = <{macro_tap}>;
            wait-ms = <{macro_wait}>;
            bindings = <&macro_press &kp LCTRL &kp LSHFT>
                     , <&macro_tap &kp U>
                     , <&macro_release &kp LCTRL &kp LSHFT>
                     , <&macro_tap &kp NUMBER_0 &kp NUMBER_3 &kp NUMBER_9 &kp NUMBER_4 &kp RET>;
        }};

        uc_pi: uc_pi {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            tap-ms = <{macro_tap}>;
            wait-ms = <{macro_wait}>;
            bindings = <&macro_press &kp LCTRL &kp LSHFT>
                     , <&macro_tap &kp U>
                     , <&macro_release &kp LCTRL &kp LSHFT>
                     , <&macro_tap &kp NUMBER_0 &kp NUMBER_3 &kp C &kp NUMBER_0 &kp RET>;
        }};

        uc_ohm: uc_ohm {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            tap-ms = <{macro_tap}>;
            wait-ms = <{macro_wait}>;
            bindings = <&macro_press &kp LCTRL &kp LSHFT>
                     , <&macro_tap &kp U>
                     , <&macro_release &kp LCTRL &kp LSHFT>
                     , <&macro_tap &kp NUMBER_0 &kp NUMBER_3 &kp A &kp NUMBER_9 &kp RET>;
        }};
    }};\n"""

    final_content = top_part + "\n".join(new_keymap) + "\n"

    with open(keymap_path, 'w') as f:
        f.write(final_content)

    print(f"Successfully updated {keymap_path}")

if __name__ == "__main__":
    generate_keymap()
