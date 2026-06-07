#!/usr/bin/env python3
import csv
import re
import sys
import os
import zipfile
import xml.etree.ElementTree as ET

KEYMAP_PATH = "boards/shields/optimized_fitness/optimized_fitness.keymap"
ATTRIBUTES_PATH = "key_attributes.csv"
ODS_PATH = "keyboard_config.ods"

PINS = {
    1: "P0.06", 2: "P0.08", 3: "P0.17", 4: "P0.20", 5: "P0.22",
    6: "P0.24", 7: "P1.00", 8: "P0.11", 9: "P1.04", 10: "P1.06",
    11: "P0.06", 12: "P0.08", 13: "P0.17", 14: "P0.20", 15: "P0.22",
    16: "P0.24", 17: "P1.00", 18: "P0.11", 19: "P1.04", 20: "P1.06"
}

def parse_keymap_file():
    if not os.path.exists(KEYMAP_PATH):
        print(f"Error: Keymap file '{KEYMAP_PATH}' not found.", file=sys.stderr)
        sys.exit(1)
        
    with open(KEYMAP_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the keymap block
    keymap_match = re.search(r"keymap\s*\{", content)
    if not keymap_match:
        print("Error: Could not find 'keymap {' in keymap file.", file=sys.stderr)
        sys.exit(1)

    keymap_start = keymap_match.start()
    
    # Brace matching to find the end of the keymap block
    depth = 0
    keymap_end = -1
    for i in range(keymap_start, len(content)):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                keymap_end = i
                break

    if keymap_end == -1:
        print("Error: Could not find matching closing brace for keymap.", file=sys.stderr)
        sys.exit(1)

    if keymap_end + 1 < len(content) and content[keymap_end+1] == ';':
        keymap_end += 1

    prefix = content[:keymap_start]
    suffix = content[keymap_end+1:]

    # Parse individual layers inside the keymap block
    keymap_inner = content[keymap_match.end():keymap_end]
    
    layers = []
    i = 0
    while i < len(keymap_inner):
        brace_start = keymap_inner.find("{", i)
        if brace_start == -1:
            break
        
        header = keymap_inner[i:brace_start].strip()
        # Clean comments
        header_clean = re.sub(r"//.*", "", header)
        header_clean = re.sub(r"/\*.*?\*/", "", header_clean, flags=re.DOTALL)
        header_tokens = header_clean.split()
        
        # Skip compatible statements or other non-layer properties
        if not header_tokens or "=" in header_clean:
            semicolon = keymap_inner.find(";", i)
            if semicolon != -1 and semicolon < brace_start:
                i = semicolon + 1
            else:
                # Find matching brace and skip
                depth = 1
                for j in range(brace_start + 1, len(keymap_inner)):
                    if keymap_inner[j] == '{':
                        depth += 1
                    elif keymap_inner[j] == '}':
                        depth -= 1
                        if depth == 0:
                            i = j + 1
                            break
            continue

        layer_name = header_tokens[-1]
        
        # Find matching brace for this layer
        depth = 1
        layer_end = -1
        for j in range(brace_start + 1, len(keymap_inner)):
            if keymap_inner[j] == '{':
                depth += 1
            elif keymap_inner[j] == '}':
                depth -= 1
                if depth == 0:
                    layer_end = j
                    break

        if layer_end == -1:
            print(f"Error: Could not find closing brace for layer '{layer_name}'.", file=sys.stderr)
            sys.exit(1)

        layer_body = keymap_inner[brace_start+1:layer_end]
        
        # Extract bindings
        bindings_match = re.search(r"bindings\s*=\s*<(.*?)>", layer_body, re.DOTALL)
        if not bindings_match:
            print(f"Error: Could not find bindings for layer '{layer_name}'.", file=sys.stderr)
            sys.exit(1)
            
        bindings_raw = bindings_match.group(1)
        # Clean comments
        bindings_clean = re.sub(r"//.*", "", bindings_raw)
        bindings_clean = re.sub(r"/\*.*?\*/", "", bindings_clean, flags=re.DOTALL)
        
        tokens = bindings_clean.split()
        
        # Group tokens starting with &
        bindings = []
        curr = []
        for t in tokens:
            if t.startswith("&"):
                if curr:
                    bindings.append(" ".join(curr))
                curr = [t]
            else:
                curr.append(t)
        if curr:
            bindings.append(" ".join(curr))
            
        layers.append((layer_name, bindings))
        i = layer_end + 1

    return prefix, suffix, layers

def read_key_metadata():
    metadata = {}
    if not os.path.exists(ATTRIBUTES_PATH):
        print(f"Warning: '{ATTRIBUTES_PATH}' not found. Using defaults.", file=sys.stderr)
        return metadata

    with open(ATTRIBUTES_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                idx = int(row["Index"])
                metadata[idx] = {
                    "Main": row.get("Main", ""),
                    "Doigt": row.get("Doigt", ""),
                    "Rangée": row.get("Rangée", ""),
                    "Colonne": row.get("Colonne", "")
                }
            except (ValueError, KeyError):
                continue
    return metadata

def parse_binding(binding):
    binding = binding.strip()
    if not binding:
        return "", "", "", "", ""
    
    parts = binding.split(maxsplit=1)
    behavior = parts[0]
    args_str = parts[1] if len(parts) > 1 else ""
    
    tap_key = ""
    tap_mod = ""
    hold_key = ""
    hold_mod = ""
    
    def parse_key_param(param):
        param = param.strip()
        m = re.match(r"^([A-Z0-9_]+)\((.*)\)$", param)
        if m:
            return m.group(2), m.group(1)
        return param, ""
        
    if behavior == "&ht":
        args = args_str.split()
        if len(args) >= 2:
            hold_arg = args[0]
            tap_arg = " ".join(args[1:])
            hold_key, hold_mod = parse_key_param(hold_arg)
            tap_key, tap_mod = parse_key_param(tap_arg)
        elif len(args) == 1:
            hold_key, hold_mod = parse_key_param(args[0])
    elif behavior == "&mtl":
        args = args_str.split()
        if len(args) >= 2:
            hold_mod = args[0]
            tap_mod = args[1]
            hold_key = "&to"
            tap_key = "&sl"
    elif behavior == "&kp":
        tap_key, tap_mod = parse_key_param(args_str)
    else:
        tap_key = args_str
        
    return behavior, tap_key, tap_mod, hold_key, hold_mod

def recompose_binding(behavior, tap_key, tap_mod, hold_key, hold_mod):
    behavior = behavior.strip()
    if not behavior:
        return "&trans"
        
    if not behavior.startswith("&"):
        behavior = "&" + behavior
        
    if behavior in ["&trans", "&none", "&studio_unlock"]:
        return behavior
        
    if behavior == "&ht":
        hold_arg = f"{hold_mod}({hold_key})" if hold_mod else hold_key
        tap_arg = f"{tap_mod}({tap_key})" if tap_mod else tap_key
        if not hold_arg and not tap_arg:
            return "&trans"
        return f"&ht {hold_arg} {tap_arg}"
        
    if behavior == "&kp":
        tap_arg = f"{tap_mod}({tap_key})" if tap_mod else tap_key
        if not tap_arg:
            return "&trans"
        return f"&kp {tap_arg}"
        
    if behavior == "&mtl":
        def extract_num(arg, fallback):
            arg = str(arg).strip()
            if not arg:
                return fallback
            digits = re.findall(r"\d+", arg)
            if digits:
                return digits[0]
            return fallback
            
        hold_val = extract_num(hold_mod, extract_num(hold_key, "1"))
        tap_val = extract_num(tap_mod, extract_num(tap_key, "1"))
        return f"&mtl {hold_val} {tap_val}"
        
    return f"{behavior} {tap_key}" if tap_key else behavior

def read_ods_sheets(ods_path):
    if not os.path.exists(ods_path):
        print(f"Error: ODS file '{ods_path}' not found.", file=sys.stderr)
        sys.exit(1)
        
    with zipfile.ZipFile(ods_path, 'r') as z:
        content = z.read('content.xml')
        root = ET.fromstring(content)
        
    ns = {
        'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
        'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
        'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
    }
    
    sheets_data = {}
    for table in root.findall('.//table:table', ns):
        sheet_name = table.get('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}name')
        
        rows = []
        for row in table.findall('.//table:table-row', ns):
            row_repeated = row.get('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}number-rows-repeated')
            row_count = int(row_repeated) if row_repeated else 1
            
            cells = []
            for cell in row.findall('.//table:table-cell', ns):
                cell_repeated = cell.get('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}number-columns-repeated')
                col_count = int(cell_repeated) if cell_repeated else 1
                
                text_nodes = cell.findall('.//text:p', ns)
                val = ''.join(''.join(t.itertext()) for t in text_nodes) if text_nodes else ''
                
                if not val and col_count > 50:
                    col_count = 1
                    
                for _ in range(col_count):
                    cells.append(val)
            
            while cells and not cells[-1]:
                cells.pop()
                
            if not any(cells):
                if row_count > 5:
                    row_count = 1
                    
            for _ in range(row_count):
                rows.append(cells)
                
        sheets_data[sheet_name] = rows
    return sheets_data

def xml_escape(val):
    return str(val).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')

def make_cell_xml(val):
    if val is None or val == "":
        return "<table:table-cell/>"
        
    try:
        float_val = float(val)
        if float_val.is_integer():
            val_str = str(int(float_val))
        else:
            val_str = str(float_val)
        return f'<table:table-cell office:value-type="float" office:value="{val_str}" calcext:value-type="float"><text:p>{val_str}</text:p></table:table-cell>'
    except ValueError:
        pass
        
    escaped = xml_escape(val)
    return f'<table:table-cell office:value-type="string" calcext:value-type="string"><text:p>{escaped}</text:p></table:table-cell>'

def make_row_xml(cells):
    row_xml = ['<table:table-row table:style-name="ro1">']
    for cell in cells:
        row_xml.append(make_cell_xml(cell))
    row_xml.append('</table:table-row>')
    return "".join(row_xml)

def write_ods_sheets(template_ods_path, output_ods_path, layers, metadata):
    other_files = {}
    content_xml_template = ""
    
    if os.path.exists(template_ods_path):
        with zipfile.ZipFile(template_ods_path, 'r') as z_in:
            content_xml_template = z_in.read('content.xml').decode('utf-8')
            for name in z_in.namelist():
                if name != 'content.xml':
                    other_files[name] = z_in.read(name)
    else:
        print(f"Error: Template ODS file '{template_ods_path}' not found. Cannot generate new ODS without template.", file=sys.stderr)
        sys.exit(1)
        
    body_idx = content_xml_template.find('<office:body>')
    if body_idx == -1:
        print("Error: Could not find <office:body> in template content.xml", file=sys.stderr)
        sys.exit(1)
        
    pre_body = content_xml_template[:body_idx]
    
    body_parts = []
    body_parts.append("<office:body>")
    body_parts.append("<office:spreadsheet>")
    body_parts.append('<table:calculation-settings table:automatic-find-labels="false" table:use-regular-expressions="false" table:use-wildcards="true"/>')
    
    for layer_name, bindings in layers:
        body_parts.append(f'<table:table table:name="{xml_escape(layer_name)}" table:style-name="ta1">')
        body_parts.append('<table:table-column table:style-name="co1" table:number-columns-repeated="9" table:default-cell-style-name="Default"/>')
        body_parts.append('<table:table-row table:style-name="ro1"><table:table-cell table:number-columns-repeated="9"/></table:table-row>')
        
        header = ["", "key index", "main", "doigt", "behavior", "tap key", "tap option", "hold key", "hold option"]
        body_parts.append(make_row_xml(header))
        
        for idx in range(1, 21):
            meta = metadata.get(idx, {"Main": "", "Doigt": ""})
            hand = meta["Main"].lower() if meta["Main"] else ""
            finger = meta["Doigt"]
            
            binding = bindings[idx - 1] if idx - 1 < len(bindings) else "&trans"
            behavior, tap_key, tap_mod, hold_key, hold_mod = parse_binding(binding)
            
            row_data = ["", idx, hand, finger, behavior, tap_key, tap_mod, hold_key, hold_mod]
            body_parts.append(make_row_xml(row_data))
            
        body_parts.append('</table:table>')
        
    key_guide = [
        ["Lettres", "A, B, C, ... Z", "Lettres standards de A a Z (attention au layout OS)", "&kp A", "Touche A"],
        ["Modificateurs combines", "LS(code)", "Shift + code", "&kp LS(S)", "Touche S majuscule"],
        ["Modificateurs combines", "LC(code)", "Ctrl + code", "&kp LC(C)", "Touche Ctrl + C (Copier)"],
        ["Modificateurs combines", "LA(code)", "Alt + code", "&kp LA(TAB)", "Alt + Tab"],
        ["Modificateurs combines", "LG(code)", "Win/Cmd + code", "&kp LG(E)", "Win + E (Ouvre l'explorateur)"],
        ["Modificateurs de base", "LSHIFT / RSHIFT", "Touche Shift (Majuscule) gauche/droite", "&kp LSHIFT", "Maintenir Shift"],
        ["Modificateurs de base", "LCTRL / RCTRL", "Touche Ctrl (Controle) gauche/droite", "&kp LCTRL", "Maintenir Ctrl"],
        ["Modificateurs de base", "LALT / RALT", "Touche Alt gauche/droite", "&kp LALT", "Maintenir Alt"],
        ["Modificateurs de base", "LGUI / RGUI", "Touche Windows / Command gauche/droite", "&kp LGUI", "Maintenir Windows/Cmd"],
        ["Ponctuation", "SQT", "Guillemet simple (Single Quote : ') ", "&kp SQT", "Touche '"],
        ["Ponctuation", "COMMA / DOT", "Virgule (,) / Point (.)", "&kp COMMA", "Touche ,"],
        ["Ponctuation", "MINUS / UNDER", "Tiret (-) / Tiret bas (_)", "&kp MINUS", "Touche -"],
        ["Touches speciales", "SPC / TAB", "Espace (Space) / Tabulation (Tab)", "&kp SPC", "Touche Espace"],
        ["Touches speciales", "RET / ESC", "Entree (Return) / Echap (Escape)", "&kp RET", "Touche Entree"],
        ["Touches speciales", "BSPC / DEL", "Retour arriere (Backspace) / Suppr (Delete)", "&kp BSPC", "Touche Retour arriere"],
        ["Navigation", "UP / DOWN", "Fleche Haut / Fleche Bas", "&kp UP", "Fleche Haut"],
        ["Navigation", "LEFT / RIGHT", "Fleche Gauche / Fleche Droite", "&kp LEFT", "Fleche Gauche"],
        ["Bluetooth", "BT_CLR", "Efface la liaison Bluetooth active", "&bt BT_CLR", "Efface l'appairage"],
        ["Bluetooth", "BT_PRV / BT_NXT", "Profil Bluetooth precedent / suivant", "&bt BT_PRV", "Passe au profil precedent"],
        ["Bluetooth", "BT_SEL 0 / 1 / 2", "Selectionne le profil Bluetooth 0, 1, 2", "&bt BT_SEL 0", "Se connecte au profil 0"]
    ]
    body_parts.append('<table:table table:name="Key" table:style-name="ta1">')
    body_parts.append('<table:table-column table:style-name="co1" table:number-columns-repeated="5" table:default-cell-style-name="Default"/>')
    body_parts.append(make_row_xml(["Categorie", "Code ZMK", "Description", "Exemple d'utilisation", "Explication"]))
    for row in key_guide:
        body_parts.append(make_row_xml(row))
    body_parts.append('</table:table>')
    
    behavior_guide = [
        ["&kp", "Key Press", "Appuie sur une touche standard", "1", "&kp A", "Appuie sur la touche 'A'"],
        ["&ht", "Hold-Tap", "Comportement different si maintenu ou tape", "2", "&ht LS(S) S", "Maintenu = Shift + S, Tape = S"],
        ["&mo", "Momentary Layer", "Active un calque temporairement pendant le maintien", "1", "&mo 1", "Active le calque 1 tant que la touche est enfoncee"],
        ["&sl", "Sticky Layer", "Active un calque pour la prochaine touche pressee uniquement", "1", "&sl 1", "Active le calque 1 pour un seul appui"],
        ["&tog", "Toggle Layer", "Active/desactive un calque de maniere permanente", "1", "&tog 2", "Bascule l'etat (ON/OFF) du calque 2"],
        ["&trans", "Transparent", "Herite de la touche definie au calque inferieur", "0", "&trans", "Laisse passer la touche du calque en dessous"],
        ["&none", "None", "Desactive completement la touche physique", "0", "&none", "Aucune action ne se produit"],
        ["&bt", "Bluetooth", "Gere les profils et connexions Bluetooth", "1 ou 2", "&bt BT_CLR", "Efface la connexion Bluetooth actuelle"],
        ["&out", "Output selection", "Selectionne la sortie USB ou Bluetooth", "1", "&out OUT_TOG", "Alterne entre USB et Bluetooth"],
        ["&studio_unlock", "Studio Unlock", "Deverrouille la connexion avec ZMK Studio", "0", "&studio_unlock", "Active le mode appairage ZMK Studio"],
        ["&mtl", "Mo-Tap-Layer", "Active un calque si maintenu, ou un Sticky calque si tape", "2", "&mtl 1 1", "Maintenu = active calque 1, Tape = sticky calque 1"],
        ["&to", "To Layer", "Active un calque de maniere permanente et desactive les autres", "1", "&to 1", "Active le calque 1"]
    ]
    body_parts.append('<table:table table:name="Behavior" table:style-name="ta1">')
    body_parts.append('<table:table-column table:style-name="co1" table:number-columns-repeated="6" table:default-cell-style-name="Default"/>')
    body_parts.append(make_row_xml(["Comportement", "Nom", "Description", "Nombre d'arguments", "Exemple de syntaxe", "Explication de l'exemple"]))
    for row in behavior_guide:
        body_parts.append(make_row_xml(row))
    body_parts.append('</table:table>')
    
    body_parts.append("</office:spreadsheet>")
    body_parts.append("</office:body>")
    body_parts.append("</office:document-content>")
    
    new_content_xml = pre_body + "".join(body_parts)
    
    with zipfile.ZipFile(output_ods_path, 'w', zipfile.ZIP_DEFLATED) as z_out:
        if 'mimetype' in other_files:
            z_out.writestr('mimetype', other_files['mimetype'], compress_type=zipfile.ZIP_STORED)
        else:
            z_out.writestr('mimetype', 'application/vnd.oasis.opendocument.spreadsheet', compress_type=zipfile.ZIP_STORED)
            
        z_out.writestr('content.xml', new_content_xml.encode('utf-8'))
        
        for name, data in other_files.items():
            if name != 'mimetype':
                z_out.writestr(name, data)

def export_to_ods(layers, metadata):
    tmp_path = ODS_PATH + ".tmp"
    try:
        write_ods_sheets(ODS_PATH, tmp_path, layers, metadata)
        if os.path.exists(ODS_PATH):
            os.remove(ODS_PATH)
        os.rename(tmp_path, ODS_PATH)
        print(f"Successfully generated '{ODS_PATH}' with {len(layers)} layers and documentation sheets.")
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        print(f"Error during export: {e}", file=sys.stderr)
        sys.exit(1)

def import_from_ods():
    sheets = read_ods_sheets(ODS_PATH)
    
    layer_names = []
    layers_data = {}
    
    for sheet_name, rows in sheets.items():
        if sheet_name in ["Key", "Behavior"]:
            continue
            
        header_row = -1
        for idx, r in enumerate(rows):
            r_norm = [c.strip().lower() for c in r]
            if 'key index' in r_norm:
                header_row = idx
                break
                
        if header_row == -1:
            print(f"Warning: Could not find 'key index' header in sheet '{sheet_name}'. Skipping.", file=sys.stderr)
            continue
            
        header_cells = [c.strip().lower() for c in rows[header_row]]
        col_map = {}
        for col_name in ['key index', 'behavior', 'tap key', 'tap option', 'tap key modifyer', 'tap key modifier', 'hold key', 'hold option', 'hold key modifyer', 'hold key modifier']:
            if col_name in header_cells:
                col_map[col_name] = header_cells.index(col_name)
                
        if 'key index' not in col_map or 'behavior' not in col_map:
            print(f"Warning: Sheet '{sheet_name}' is missing mandatory columns. Skipping.", file=sys.stderr)
            continue
            
        bindings = ["&trans"] * 20
        required_len = max(col_map.values()) + 1 if col_map else 0
        for r in rows[header_row + 1:]:
            if len(r) < required_len:
                r = r + [""] * (required_len - len(r))
                
            key_idx_val = r[col_map['key index']]
            if not key_idx_val:
                continue
                
            try:
                key_idx = int(float(key_idx_val))
            except ValueError:
                continue
                
            if key_idx < 1 or key_idx > 20:
                continue
                
            behavior = r[col_map['behavior']]
            tap_key = r[col_map['tap key']] if 'tap key' in col_map else ''
            
            tap_mod_col = col_map.get('tap option', col_map.get('tap key modifyer', col_map.get('tap key modifier')))
            tap_mod = r[tap_mod_col] if tap_mod_col is not None else ''
            
            hold_key = r[col_map['hold key']] if 'hold key' in col_map else ''
            
            hold_mod_col = col_map.get('hold option', col_map.get('hold key modifyer', col_map.get('hold key modifier')))
            hold_mod = r[hold_mod_col] if hold_mod_col is not None else ''
            
            bindings[key_idx - 1] = recompose_binding(behavior, tap_key, tap_mod, hold_key, hold_mod)
            
        layer_names.append(sheet_name)
        layers_data[sheet_name] = bindings
        
    return layer_names, layers_data

def import_from_csv():
    # Deprecated: use ODS functions instead. Left as compatibility placeholder.
    pass

def export_to_csv(layers, metadata):
    # Deprecated: use ODS functions instead. Left as compatibility placeholder.
    pass

def generate_keymap_content(prefix, suffix, layer_names, layers_data):
    out = []
    out.append(prefix.rstrip())
    out.append("    keymap {")
    out.append('        compatible = "zmk,keymap";')
    out.append("")

    for layer_name in layer_names:
        bindings = layers_data[layer_name]
        out.append(f"        {layer_name} {{")
        out.append("            bindings = <")

        out.append("                // Left hand (Index 1 to 10)")
        for idx in range(1, 11):
            binding = bindings[idx - 1]
            comment = f"// {idx}"
            if layer_name == "layer_1" and idx in PINS:
                comment += f"  ({PINS[idx]})"
            out.append(f"                {binding:<27} {comment}")

        out.append("")
        out.append("                // Right hand (Index 11 to 20)")
        for idx in range(11, 21):
            binding = bindings[idx - 1]
            comment = f"// {idx}"
            if layer_name == "layer_1" and idx in PINS:
                comment += f"  ({PINS[idx]})"
            out.append(f"                {binding:<27} {comment}")

        out.append("            >;")
        out.append("        };")
        out.append("")

    out.append("    };")
    out.append(suffix.lstrip())

    return "\n".join(out)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--import":
        print("Importing config from ODS to update keymap...")
        prefix, suffix, _ = parse_keymap_file()
        layer_names, layers_data = import_from_ods()
        new_content = generate_keymap_content(prefix, suffix, layer_names, layers_data)
        with open(KEYMAP_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Successfully updated '{KEYMAP_PATH}' from ODS configuration.")
    else:
        print("Exporting keymap config to ODS...")
        prefix, suffix, layers = parse_keymap_file()
        metadata = read_key_metadata()
        export_to_ods(layers, metadata)

if __name__ == "__main__":
    main()
