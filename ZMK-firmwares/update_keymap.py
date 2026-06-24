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

    def pad(text, width=27):
        return text.ljust(width)

    def format_binding(tap):
        if not tap:
            return "&trans"
        
        tap = tap.replace("RSHIFT(", "RS(").replace("LSHIFT(", "LS(")
        tap = tap.replace("RCTRL(", "RC(").replace("LCTRL(", "LC(")
        tap = tap.replace("RALT(", "RA(").replace("LALT(", "LA(")
        tap = tap.replace("RGUI(", "RG(").replace("LGUI(", "LG(")
        
        if not tap.startswith("&") and tap != "":
            tap = tap.upper()
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
            if tap in aliases:
                tap = aliases[tap]
            tap = f"&kp {tap}"
            
        return tap

    new_keymap = []
    new_keymap.append('    keymap {')
    new_keymap.append('        compatible = "zmk,keymap";\n')

    for layer in range(16):
        layer_str = str(layer)
        new_keymap.append(f'        layer_{layer + 1} {{')
        new_keymap.append('            bindings = <')
        new_keymap.append('                // Left hand (Index 1 to 10)')
        
        for i in range(1, 11):
            binding = "&trans"
            if i in keys_by_index:
                b = keys_by_index[i].get("bindings", {}).get(layer_str, {})
                tap = b.get("tap", "").strip()
                binding = format_binding(tap)
            new_keymap.append(f'                {pad(binding)}// {i}')
            
        new_keymap.append('')
        new_keymap.append('                // Right hand (Index 11 to 20)')
        for i in range(11, 21):
            binding = "&trans"
            if i in keys_by_index:
                b = keys_by_index[i].get("bindings", {}).get(layer_str, {})
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
