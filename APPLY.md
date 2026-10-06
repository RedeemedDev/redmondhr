# APPLY — RedmondHR employees list sort toggle (2026-10-06)

Adam applies via archive extract. Unpack `redmondhr-files-sort-toggle-2026-10-06.tar.gz` over the project root (relative paths), or replace each file below with the full contents from `/workspace/redmondhr`.

## Files to replace (this batch)

| Path |
|------|
| `app/crud.py` |
| `app/routers/employees.py` |
| `app/templates/employees_list.html` |
| `README.md` |

Optional: `APPLY.md` (this file).

**No schema migration.** Restart uvicorn after replacing files.

## What changed (for Carl)

1. **Clickable column headers toggle sort direction**
   - First click on a column → ascending / natural primary direction
   - Second click on same column → reverse
   - Click a different column → that column starts ascending
   - Query params: `sort=name|hire|role|specialty|wage` and `dir=asc|desc` (alias `order=`)
   - Search `q` is preserved when toggling
   - Active column shows ▴ (asc) or ▾ (desc)

2. **Sort dropdown removed** — headers are the primary UX; search form kept (preserves current sort/dir via hidden fields)

3. **`list_employees(..., direction=)`** reverses all five sorts when `direction=desc`

### URL examples

- `/employees` — name A→Z (default)
- `/employees?sort=name&dir=desc` — name Z→A
- `/employees?sort=hire&dir=asc` — earliest hire first
- `/employees?sort=hire&dir=desc` — latest hire first
- `/employees?sort=role&dir=asc` — Year 1 → Team Lead
- `/employees?sort=specialty&dir=desc` — reverse specialty order
- `/employees?sort=wage&dir=asc&q=Chen` — low→high wage, filtered

## Smoke checks (local)

```bat
.venv\Scripts\python -c "from app.crud import list_employees; a=list_employees(sort='name', direction='asc'); d=list_employees(sort='name', direction='desc'); assert [e['name'] for e in a]==list(reversed([e['name'] for e in d])) or len(a)<2; print('name ok', len(a)); h=list_employees(sort='hire', direction='asc'); print('hire first', h[0].get('name') if h else None); print('ok')"
```

Then restart: `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
