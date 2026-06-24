import zipfile
import xml.etree.ElementTree as ET
import os

ods_path = "keyboard_config.ods"
if not os.path.exists(ods_path):
    print("ODS file not found")
    exit(1)

with zipfile.ZipFile(ods_path, 'r') as z:
    content = z.read('content.xml')
    root = ET.fromstring(content)

ns = {
    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
}

for table in root.findall('.//table:table', ns):
    sheet_name = table.get('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}name')
    if sheet_name in ["Key", "Behavior"]:
        continue
    print(f"\n--- Layer: {sheet_name} ---")
    rows = []
    for row in table.findall('.//table:table-row', ns):
        cells = []
        for cell in row.findall('.//table:table-cell', ns):
            text_nodes = cell.findall('.//text:p', ns)
            val = ''.join(''.join(t.itertext()) for t in text_nodes) if text_nodes else ''
            cells.append(val)
        rows.append(cells)
    
    header_row = -1
    for idx, r in enumerate(rows):
        r_norm = [c.strip().lower() for c in r]
        if 'key index' in r_norm:
            header_row = idx
            break
            
    if header_row == -1:
        continue
        
    header_cells = [c.strip().lower() for c in rows[header_row]]
    col_map = {}
    for col_name in ['key index', 'behavior', 'tap key', 'tap option', 'hold key', 'hold option']:
        if col_name in header_cells:
            col_map[col_name] = header_cells.index(col_name)
            
    for r in rows[header_row + 1:]:
        if len(r) < len(header_cells):
            continue
        key_idx_val = r[col_map['key index']] if 'key index' in col_map else ''
        if not key_idx_val:
            continue
        try:
            key_idx = int(float(key_idx_val))
        except ValueError:
            continue
        behavior = r[col_map['behavior']] if 'behavior' in col_map else ''
        tap_key = r[col_map['tap key']] if 'tap key' in col_map else ''
        tap_opt = r[col_map['tap option']] if 'tap option' in col_map else ''
        hold_key = r[col_map['hold key']] if 'hold key' in col_map else ''
        hold_opt = r[col_map['hold option']] if 'hold option' in col_map else ''
        if behavior not in ["", "&trans"]:
            print(f"  Key {key_idx}: behavior={behavior}, tap={tap_key}({tap_opt}), hold={hold_key}({hold_opt})")
