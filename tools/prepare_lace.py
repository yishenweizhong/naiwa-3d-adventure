"""Cut the supplied illustration's lace panel; never ship the full reference."""
from PIL import Image
from pathlib import Path
import argparse

parser=argparse.ArgumentParser()
parser.add_argument("reference",type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
image=Image.open(args.reference).convert("RGBA")
assert image.size==(1920,2560), "Crop coordinates require the selected 1920 × 2560 illustration."
# A chain-free detail provides continuous fabric on the shaped 3D blouse.
detail=image.crop((1055,1550,1148,1728)).convert("RGB")
detail=detail.resize((186,356))
tile=Image.new("RGB",(372,712))
tile.paste(detail,(0,0)); tile.paste(detail.transpose(Image.Transpose.FLIP_LEFT_RIGHT),(186,0))
tile.paste(tile.crop((0,0,372,356)).transpose(Image.Transpose.FLIP_TOP_BOTTOM),(0,356))
tile.save(root/"public/textures/lace-fabric.png",optimize=True)
print("Reference lace fabric:",tile.size)
