import RLPy
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

avatar = RLPy.RScene.GetAvatars()[0]
shaping_comp = avatar.GetAvatarShapingComponent()

output_path = str(_ROOT / "Detailed_Morph_Dictionary.txt")

with open(output_path, "w", encoding="utf-8") as file:
    categories = shaping_comp.GetShapingMorphCatergoryNames()

    for cat in categories:
        file.write(f"\n========== KATEGORİ: {cat} ==========\n")

        ids   = shaping_comp.GetShapingMorphIDs(cat)
        names = shaping_comp.GetShapingMorphDisplayNames(cat)

        if ids and names:
            for i in range(len(ids)):
                result = shaping_comp.GetShapingMorphMinMax(ids[i])
                min_val, max_val = result[1], result[2]
                file.write(
                    f"UI İsmi: {names[i]}  |  "
                    f"Kod ID: {ids[i]}  |  "
                    f"Range: [{min_val}, {max_val}]\n"
                )
        else:
            file.write("Bu kategoride slider bulunamadi.\n")

print(f"Hazır! {output_path}")