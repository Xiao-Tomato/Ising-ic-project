# stitch_ising_11.py — single ribbon, min-cut seams, LowT→HighT, NO labels/arrow
import os
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter


BETAS = ["0.30","0.34","0.38","0.41","0.43","0.44","0.45","0.47","0.50","0.55","0.60"]
BASE_DIR = os.path.expanduser("~/Desktop/8 neibors")
OUT_PATH = os.path.join(BASE_DIR, "ising_long_11.png")


ORDER_LOW_TO_HIGH_T = True


STRIP_RATIO   = 0.60  
VSTRIP_RATIO = 0.75  
OVLP_RATIO    = 0.22   
SEAM_SOFTEN   = 1.2   


PAD_PX        = 0     
SHOW_TICKS    = False  
AUTOCROP_WHITE = True
CROP_BG        = (255,255,255)
CROP_TOL       = 10

VERBOSE = True
# ==========================

def log(*a):
    if VERBOSE: print("[stitch]", *a)

def autocrop_white(im):
    if im.mode != "RGB": im_rgb = im.convert("RGB")
    else: im_rgb = im
    bg_img = Image.new("RGB", im_rgb.size, CROP_BG)
    diff = ImageChops.difference(im_rgb, bg_img)
    bbox = diff.convert("L").point(lambda p: 255 if p > CROP_TOL else 0).getbbox()
    return im.crop(bbox) if bbox else im

def load_images(paths):
    imgs = []
    for p in paths:
        im = Image.open(p).convert("RGBA")
        if AUTOCROP_WHITE:
            im = autocrop_white(im)
        imgs.append(im)
        log("loaded", os.path.basename(p), "->", im.size)
    return imgs

def normalize_height(imgs):

    min_h = min(im.height for im in imgs)
    outs = []
    for im in imgs:
        if im.height == min_h:
            outs.append(im)
        else:
            new_w = int(round(im.width * (min_h / im.height)))
            outs.append(im.resize((new_w, min_h), Image.LANCZOS))
            log("downscale to", new_w, "x", min_h)
    return outs

def crop_visible_center(imgs, ratio):
    outs = []
    for im in imgs:
        crop_w = max(8, int(round(im.width * ratio)))
        left = max(0, (im.width - crop_w)//2)
        outs.append(im.crop((left, 0, left + crop_w, im.height)))
    return outs

def crop_vertical_center(im, ratio):
    h = im.height
    crop_h = max(8, int(round(h * ratio)))
    top = (h - crop_h) // 2
    return im.crop((0, top, im.width, top + crop_h))


def mincut_seam_mask(L_ov, R_ov):
    L = L_ov.convert("L"); R = R_ov.convert("L")
    w, h = L.size
    Lp, Rp = L.load(), R.load()

    cost = [[0]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            cost[y][x] = abs(Lp[x,y] - Rp[x,y])

    acc  = [[0]*w for _ in range(h)]
    back = [[0]*w for _ in range(h)]
    for x in range(w):
        acc[0][x] = cost[0][x]; back[0][x] = x
    for y in range(1, h):
        for x in range(w):
            best, bx = acc[y-1][x], x
            if x>0   and acc[y-1][x-1]<best: best, bx = acc[y-1][x-1], x-1
            if x<w-1 and acc[y-1][x+1]<best: best, bx = acc[y-1][x+1], x+1
            acc[y][x] = cost[y][x] + best; back[y][x] = bx
    seam=[0]*h; x = min(range(w), key=lambda j: acc[h-1][j])
    for y in range(h-1, -1, -1):
        seam[y] = x; x = back[y][x]
    mask = Image.new("L", (w, h), 0); mp = mask.load()
    for y, sx in enumerate(seam):
        for x in range(sx, w): mp[x, y] = 255
    if SEAM_SOFTEN and SEAM_SOFTEN > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=float(SEAM_SOFTEN)))
    return mask

def stitch_pair(L, R, ovlp_px):
    H = L.height
    ov = int(max(2, min(ovlp_px, L.width, R.width)))
    L_ov = L.crop((L.width - ov, 0, L.width, H))
    R_ov = R.crop((0, 0, ov, H))
    mask = mincut_seam_mask(L_ov, R_ov)
    out = Image.new("RGBA", (L.width + R.width - ov, H))
    out.paste(L, (0,0))
    full_mask = Image.new("L", (R.width, H), 255)
    full_mask.paste(mask, (0,0))
    out.paste(R, (L.width - ov, 0), full_mask)
    return out

def main():

    betas_f = [float(b) for b in BETAS]
    order = sorted(range(len(betas_f)), key=lambda i: betas_f[i], reverse=True) if ORDER_LOW_TO_HIGH_T \
            else sorted(range(len(betas_f)), key=lambda i: betas_f[i])
    paths = [os.path.join(BASE_DIR, f"{BETAS[i]}.png") for i in order]
    miss = [p for p in paths if not os.path.exists(p)]
    if miss:
        print("not found："); [print(" -", m) for m in miss]; return

    imgs = normalize_height(load_images(paths))
    cropped = crop_visible_center(imgs, STRIP_RATIO)
    if VSTRIP_RATIO < 1.0:
        cropped = [crop_vertical_center(im, VSTRIP_RATIO) for im in cropped]



    overlaps = []
    for i in range(len(cropped)-1):
        m = min(cropped[i].width, cropped[i+1].width)
        overlaps.append(max(2, int(round(OVLP_RATIO * m))))

    combo = cropped[0]
    for i in range(1, len(cropped)):
        combo = stitch_pair(combo, cropped[i], overlaps[i-1])


    total_w = combo.width + 2*PAD_PX
    total_h = combo.height + 2*PAD_PX
    canvas = Image.new("RGBA", (total_w, total_h), (255,255,255,255))
    canvas.paste(combo, (PAD_PX, PAD_PX))

    canvas.save(OUT_PATH)
    print("Saved:", OUT_PATH)

if __name__ == "__main__":
    main()
