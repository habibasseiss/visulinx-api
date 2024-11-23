## Autogenerate migration

```sh
uv run alembic revision --autogenerate -m "add ... table"
```

## Generating secrets

```sh
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
