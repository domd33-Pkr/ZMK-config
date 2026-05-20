import json

with open("keyboard_layout_12th_final.json", "r") as f:
    data = json.load(f)

print("| Index | Main (Hand) | Doigt (Finger) | Rangée (Row) | Colonne (Col) | Base Tap | Base Hold | Layer Tap | Layer Hold | Touche Calque ? |")
print("|-------|-------------|----------------|--------------|---------------|----------|-----------|-----------|------------|-----------------|")

keys = sorted(data["keys"], key=lambda k: k["index"])

for k in keys:
    slots = k.get("slots", {})
    idx = k["index"]
    hand = k.get("hand", "")
    finger = k.get("finger", "")
    row = k.get("row", "")
    col = k.get("col", "")
    base_tap = slots.get("base_tap", "")
    base_hold = slots.get("base_hold", "")
    layer_tap = slots.get("layer_tap", "")
    layer_hold = slots.get("layer_hold", "")
    is_layer = "Oui" if k.get("is_layer_key") else "Non"
    
    print(f"| {idx} | {hand} | {finger} | {row} | {col} | {base_tap} | {base_hold} | {layer_tap} | {layer_hold} | {is_layer} |")

