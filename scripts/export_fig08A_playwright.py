from playwright.sync_api import sync_playwright
from pathlib import Path

OUT = Path("paper/figures")
OUT.mkdir(parents=True, exist_ok=True)

URL = "http://localhost:5173"   # change if different
OUTFILE = OUT / "fig08A_metaverse_3d.png"

# base viewport (pixels)
W, H = 1800, 1100

# export scale (device pixel ratio)
SCALE = 3  # try 2, 3, or 4

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=SCALE)

        page.goto(URL, wait_until="networkidle")

        # Give MapLibre time to fully render tiles + extrusions
        page.wait_for_timeout(2500)

        # If you can add an id to your map container, prefer locator("#map")
        # Otherwise screenshot the whole page:
        page.screenshot(path=str(OUTFILE), full_page=False)

        browser.close()
        print("Saved:", OUTFILE)

if __name__ == "__main__":
    main()