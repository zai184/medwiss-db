# API contract (generated)

Source of truth: FastAPI / Pydantic (`api/models.py` and routers).

```text
./scripts/gen-api.sh
  → openapi.json          (this directory, do not edit)
  → ui/src/lib/api-types.d.ts
```

`$lib/api.ts` is the one axios wrapper. It re-exports `ApiComponents` / `ApiPaths` from `api-types.d.ts`. Handwritten interfaces stay until a call site switches.
