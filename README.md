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

This is frontend UI only. Flask, database, authentication, payments and real admin persistence are added in the backend phase.

## Image note
The current UI uses locally bundled, AI-generated mock photography depicting older Kenyan community members and activities. These are placeholder visuals for the course project and should be replaced with approved organization/royalty-free assets before any real-world publication.

## Image update
The public image set has been replaced with the user-provided Pexels photography supplied for this course project. Images are locally bundled under `public/images/` and cropped/resized to match the UI's hero, card, gallery, and profile aspect ratios.


## Logo & UI palette

The frontend uses the supplied KDCCE logo at `public/images/logo.png` and derives its visual palette from that artwork: deep blue, magenta, lime green, white, and dark neutrals. The public header/footer and the admin portal use the same brand identity.

## Admin portal

The repository includes the **admin portal UI** under `/admin/login` and `/admin/*`. At this UI stage it is intentionally mock data only. The Flask backend must later provide authentication, password hashing, role-based authorization (Admin/Staff), real donation records, content CRUD, image uploads, contact inbox handling, CSV export, and audit logging. The frontend should never be treated as the security boundary; permissions must be enforced by the backend.
