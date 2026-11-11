import sys, os, subprocess, importlib
sys.path.insert(0, os.path.dirname(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
def render(outdir, pages, only=None, scale=2):
    os.makedirs(outdir, exist_ok=True)
    for name, (html, w, h) in pages.items():
        p = os.path.join(outdir, name + ".html")
        open(p, "w").write(html)
        if only and not any(o in name for o in only): continue
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}",
                        f"--window-size={w},{h}", f"--screenshot={os.path.join(outdir, name + '.png')}", "--virtual-time-budget=1500", "file://" + p],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        print("rendered", name, os.path.getsize(os.path.join(outdir, name + ".png")) // 1024, "KB")
if __name__ == "__main__":
    which = sys.argv[1]; only = sys.argv[2:] or None
    if which == "mac":
        import mac_shell
        for m in ["mac_home", "mac_conn", "mac_more"]:
            try: importlib.import_module(m)
            except ModuleNotFoundError as e:
                if m not in str(e): raise
        render(mac_shell.OUT, mac_shell.PAGES, only, scale=1.5)
    else:
        import android
        for outdir, pages in android.OUTS.items(): render(outdir, pages, only, scale=2)
