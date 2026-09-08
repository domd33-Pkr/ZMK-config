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
            "BKS": "BSPC"
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
                tap = f"{parts[0]} {clean_keycode(parts[1])} {clean_keycode(parts[2])}"
        
        if tap in ("&ht DELTA DEGREE", "&ht DELTA RA(LS(SEMI))"):
            return "&ht_delta_deg 0 0"
        if tap in ("&ht DEGREE DELTA", "&ht RA(LS(SEMI)) DELTA"):
            return "&ht_deg_delta 0 0"
        if tap == "&ht PI OHM":
            return "&ht_pi_ohm 0 0"
        if tap == "&ht OHM PI":
            return "&ht_ohm_pi 0 0"

        if tap == "&kp OHM" or tap == "OHM":
            return "&uc_ohm"
        if tap == "&kp DELTA" or tap == "DELTA":
            return "&uc_delta"
        if tap == "&kp PI" or tap == "PI":
            return "&uc_pi"
        if tap == "&kp LS(GRAVE)" or tap == "LS(GRAVE)":
            return "&single_tilde"

        if tap in ("&kp AGRAVE", "AGRAVE", "&mm_agrave", "mm_agrave"):
            return "&mm_agrave"
        if tap in ("&kp EGRAVE", "EGRAVE", "&mm_egrave", "mm_egrave"):
            return "&mm_egrave"
        if tap in ("&kp CCEDIL", "CCEDIL", "&mm_ccedilla", "mm_ccedilla"):
            return "&mm_ccedilla"
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

#define DEGREE RA(LS(SEMI))

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

        mm_agrave: mod_morph_agrave {{
            compatible = "zmk,behavior-mod-morph";
            #binding-cells = <0>;
            bindings = <&macro_agrave>, <&macro_agrave_maj>;
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
            bindings = <&kp DEGREE>;
        }};

        single_tilde: single_tilde {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            bindings = <&macro_tap &kp LS(GRAVE) &kp SPACE>;
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
