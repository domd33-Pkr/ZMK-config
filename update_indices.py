import json

mapping = {
    0: 10,  # ENT
    1: 8,   # g
    2: 6,   # LYR
    3: 4,   # m
    4: 3,   # d
    5: 9,   # p
    6: 7,   # r
    7: 5,   # n
    8: 2,   # l
    9: 1,   # s
    10: 11, # a
    11: 14, # t
    12: 16, # i
    13: 18, # v
    14: 20, # BKS
    15: 12, # c
    16: 15, # SPC
    17: 17, # e
    18: 19, # u
    19: 13, # o
}

with open("keyboard_layout_12th_final.json", "r") as f:
    data = json.load(f)

for key in data["keys"]:
    key["index"] = mapping[key["index"]]

for char, slot in data["char_to_key_slot"].items():
    slot[0] = mapping[slot[0]]

data["layer_key_index"] = mapping[data["layer_key_index"]]

new_lockedSlots = []
for slot in data["lockedSlots"]:
    parts = slot.split(",")
    new_lockedSlots.append(f"{mapping[int(parts[0])]},{parts[1]}")
data["lockedSlots"] = new_lockedSlots

with open("keyboard_layout_12th_final.json", "w") as f:
    json.dump(data, f, indent=2)

print("Done")
