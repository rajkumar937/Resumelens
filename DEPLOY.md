# ResumeLens — deployment + PWA notes

## New / changed files
```
wsgi.py                              new — production entry point
Procfile                             new — gunicorn start command
runtime.txt                          new — pins Python 3.13
render.yaml                          new — optional Render blueprint
requirements.txt                     changed — added gunicorn
.env.example                         changed — added prod vars

app/__init__.py                      changed — ProxyFix, secure cookies, logging, DB/UPLOAD env overrides
app/routes.py                        changed — added /offline and /sw.js routes
app/database.py                      changed — DB_PATH env override (1 line)
app/templates/base.html              changed — manifest link, meta tags, install button, pwa.js include
app/templates/offline.html           new — offline fallback page
app/static/manifest.json             new
app/static/sw.js                     new — service worker (app-shell only)
app/static/js/pwa.js                 new — sw registration + install prompt
app/static/css/pwa-additions.css     new — safe-area, install button, small-screen tweaks
app/static/icons/icon-192.png        new — placeholder, swap for real artwork
app/static/icons/icon-512.png        new — placeholder
app/static/icons/icon-maskable-512.png  new — placeholder
```
Not touched: `extractor.py`, `matcher.py`, `skills.py`, `main.css`, `main.js`, `run.py`, `.gitignore`, all history/analysis logic.

## Why analysis stays online-only
`sw.js` only caches the shell (`/`, css, js, manifest, icons). `/analyse` and
`/history` are excluded from caching and always go to the network, with a
network-first fallback to `/offline` — matches requirement 5.

## Local test
```bash
cd rl9fix
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                               # edit SECRET_KEY
python wsgi.py                                      # http://localhost:5000
```
Or with gunicorn directly:
```bash
gunicorn -w 2 -k gthread --threads 4 -b 0.0.0.0:5000 wsgi:app
```
PWA install/offline check: open in Chrome, DevTools → Application → Manifest
and Service Workers, confirm both registered, then toggle "Offline" and
reload `/`.

## Deploy (Render — free tier example)
1. Push repo to GitHub.
2. Render → New → Blueprint → pick repo → uses `render.yaml` automatically.
   (Or New → Web Service, Build: `pip install -r requirements.txt`,
   Start: `gunicorn -w 2 -k gthread --threads 4 -b 0.0.0.0:$PORT wsgi:app`.)
3. Add a 1 GB disk mounted at `/var/data` (already in render.yaml) so
   `resumelens.db` and uploads survive restarts — sqlite on ephemeral disk
   loses history on every redeploy otherwise.
4. Set `SECRET_KEY` (Render can auto-generate it).
5. Deploy. Visit the given `.onrender.com` URL — installable on mobile
   Chrome/Edge (Add to Home Screen) and desktop Chrome (install icon in
   the address bar).

Any other platform (Railway, Fly.io, a VPS) works the same way: install
`requirements.txt`, run the gunicorn command above, set `SECRET_KEY`,
`FLASK_ENV=production`, and point `DB_PATH`/`UPLOAD_FOLDER` at persistent
storage if the platform's filesystem is ephemeral.

## Icons
`app/static/icons/*.png` are placeholders (dark rounded square + magnifier
mark). Replace with real branded 192/512/512-maskable PNGs before a public
launch — same filenames, `manifest.json` needs no change.
