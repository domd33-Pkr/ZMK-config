#!/usr/bin/env python3
import json
import os
import re

json_path = "/home/dominic/Documents/Claviers/Key Configurator/Archives/keyboard_layout_updated.json"
keymap_path = "/home/dominic/Documents/Claviers/ZMK-config/boards/shields/optimized_fitness/optimized_fitness.keymap"

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
        
        if tap == "&kp OHM" or tap == "OHM":
            return "&uc_ohm"
        if tap == "&kp DELTA" or tap == "DELTA":
            return "&uc_delta"
        if tap == "&kp PI" or tap == "PI":
            return "&uc_pi"
        if tap == "&kp LS(GRAVE)" or tap == "LS(GRAVE)":
            return "&single_tilde"
        
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

    if not os.path.exists(keymap_path):
        print(f"Error: Keymap file not found at {keymap_path}")
        exit(1)

    with open(keymap_path, 'r') as f:
        content = f.read()

    match = re.search(r'\n\s*keymap\s*\{', content)
    if not match:
        print("Could not find 'keymap {' block in existing file!")
        exit(1)

    top_part = content[:match.start()]

    final_content = top_part + "\n" + "\n".join(new_keymap) + "\n"

    with open(keymap_path, 'w') as f:
        f.write(final_content)

    print(f"Successfully updated {keymap_path}")

if __name__ == "__main__":
    generate_keymap()
