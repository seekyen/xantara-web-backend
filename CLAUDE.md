# Claude handoff — Xantara web backend

Read `AGENTS.md` and `C:\Dev\Xantara-POS-project-knowledge.md` before making
changes. The shared knowledge file covers this Django API, the Flutter POS in
`C:\Dev\Xantara-POS`, and the Next.js admin in
`C:\Dev\xantara-web-frontend`. Later numbered entries supersede older status
text when behavior evolved.

Update the shared knowledge file after every meaningful code, schema, API,
security, setup, deployment, or architecture change. Code and tests are the
authority if documentation is stale.

## Local runtime

- Django API: `http://127.0.0.1:8000`
- Local database: MySQL `xantara_pos_db`
- Settings: `config.settings.local`
- Admin frontend: `http://127.0.0.1:3000`
- Flutter preview: `http://127.0.0.1:8086` (fixed canonical port; it proxies API
  and media requests to this backend)

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --settings=config.settings.local --noreload
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings.local
.\.venv\Scripts\python.exe manage.py test --settings=config.settings.sqlite_local
```

Fresh databases use `GET/POST /api/v1/setup/status/` for the atomic one-time
single-company setup: company profile, `MAIN` branch, first administrator, and
initial sync installation. The current local MySQL installation is already
complete as `Xantara POS` with business ID `xantara`.

Preserve invoice immutability, branch-scoped inventory, transaction boundaries,
authorization, password hashing, migration safety, and secrets handling. Do not
replace or reset existing local data merely to exercise first-run setup.
