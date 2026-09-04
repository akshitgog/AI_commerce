# Runtime configuration

Application inputs are centralized in this directory.

- `default.yaml`: committed safe defaults and complete shape.
- `local.example.yaml`: editable developer template.
- `local.yaml`: automatic local overlay, ignored by Git.
- `APP_CONFIG_FILE`: process environment variable selecting a CI/deployment YAML overlay.

```powershell
Copy-Item config/local.example.yaml config/local.yaml
```

Overlays deep-merge by section. Source precedence is explicit `Settings` values, process
environment, legacy `.env`, selected/local YAML, committed YAML and typed code defaults. Unknown
YAML sections/fields fail startup. Secret values use `SecretStr` and are redacted from settings
representations.

When adding an input, add its typed `Settings` field, YAML schema mapping, safe default/example and
tests together. Feature code must consume `Settings`, not read ad hoc environment variables.

Never commit API keys, database passwords, webhook secrets or signing secrets. Razorpay's webhook
secret is independently configured in the dashboard and is not the API key secret.
