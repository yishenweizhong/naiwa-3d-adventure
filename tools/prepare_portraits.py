"""Crop the two user-selected images. Full originals are never copied into the game."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import argparse, json

parser = argparse.ArgumentParser()
parser.add_argument("--enemy", type=Path, required=True)
parser.add_argument("--hero", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
out = root / "public/textures"
out.mkdir(parents=True, exist_ok=True)

def crop(source, reference_size, bounds, contour, name):
    image = Image.open(source).convert("RGBA")
    if image.size != reference_size:
        raise ValueError(f"{name}: expected {reference_size}, got {image.size}")
    cropped = image.crop(bounds)
    mask = Image.new("L", cropped.size)
    ImageDraw.Draw(mask).polygon(contour, fill=255)
    cropped.putalpha(mask.filter(ImageFilter.GaussianBlur(.7)))
    cropped.thumbnail((512, 640), Image.Resampling.LANCZOS)
    cropped.save(out / f"{name}.png", optimize=True)
    return {"asset": f"{name}.png", "size": cropped.size,
            "method": "Original supplied pixels, manually outlined alpha; no generated facial features"}

# Outline coordinates are local to the crop; do not erase dark hair based on colour.
enemy_contour = [(66,53),(145,35),(221,30),(305,36),(369,59),(407,105),
                 (418,168),(403,236),(391,288),(399,308),(388,346),(384,390),
                 (364,422),(356,458),(335,493),(310,529),(271,578),(212,624),
                 (158,600),(116,562),(110,519),(88,491),(70,456),(55,407),
                 (44,355),(38,311),(31,264),(22,216),(25,158),(40,93)]
enemy_contour = [(round(x*710/433), round(y*1050/640)) for x,y in enemy_contour]
records = [crop(args.enemy, (1279,1706), (315,190,1025,1240), enemy_contour, "enemy-head")]
hero_contour = [(181,30),(233,36),(291,82),(323,143),(337,200),(323,245),
                (303,276),(282,283),(262,346),(222,393),(196,414),
                (171,408),(144,390),(112,352),(80,317),(53,278),(33,223),
                (37,178),(58,114),(108,63)]
records.append(crop(args.hero, (1920,2560), (869,1006,1275,1462), hero_contour, "hero-face"))
print(json.dumps(records, ensure_ascii=False, indent=2))
