# KDCCE UI

React + Vite + Tailwind CSS frontend for the Moringa School KDCCE course project.

## Start the project

Use a terminal inside this folder:

```bash
npm install
npm run dev
```

Open the URL printed by Vite, normally:

`http://localhost:5173`

Do **not** double-click `index.html`. Vite must serve the project.

## If the page is blank

Run:

```bash
rm -rf node_modules package-lock.json
npm install
npm run dev
```

On Windows PowerShell:

```powershell
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item package-lock.json -ErrorAction SilentlyContinue
npm install
npm run dev
```

The app includes an error boundary so runtime errors display on the page instead of silently leaving a blank screen.

## Pages

- `/`
- `/about`
- `/programs`
- `/gallery`
- `/blog`
- `/blog/1`
- `/sponsor`
- `/donate`
- `/contact`
- `/crafts`
- `/admin/login`
- `/admin`

Talks to the Flask API in `../backend/` (see its README) via `src/lib/api.js` — set `VITE_API_URL` in `.env` to point at it (defaults to `http://localhost:5000`). API request/response shapes are documented per module in `../docs/api/`.

## Image note
The current UI uses locally bundled, AI-generated mock photography depicting older Kenyan community members and activities. These are placeholder visuals for the course project and should be replaced with approved organization/royalty-free assets before any real-world publication.

## Image update
The public image set has been replaced with the user-provided Pexels photography supplied for this course project. Images are locally bundled under `public/images/` and cropped/resized to match the UI's hero, card, gallery, and profile aspect ratios.


## Logo & UI palette

The frontend uses the supplied KDCCE logo at `public/images/logo.png` and derives its visual palette from that artwork: deep blue, magenta, lime green, white, and dark neutrals. The public header/footer and the admin portal use the same brand identity.

## Admin portal

The repository includes the **admin portal UI** under `/admin/login` and `/admin/*`. Donations, blog posts, gallery images, team members, and craft items are wired to the real backend (auth, RBAC, CRUD, CSV export). The Inbox tab is still mock/local state — it has no backend yet. The frontend is never the security boundary; permissions are enforced by the backend regardless of what the UI shows or hides.
