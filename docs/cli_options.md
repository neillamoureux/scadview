# Command-Line Options

Run SCADview from the command line with:

```bash
python -m scadview
```

The launcher accepts logging options and debug-info options.

## Options

`-v`, `--verbose`
: Increase verbosity. Use `-v` for INFO or `-vv` for DEBUG.

`--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`
: Set the logging level directly. This overrides `-v`/`-vv` when provided.

`--debug-info-file <path>`
: Write debug diagnostics JSON to a specific file.

`--debug-info-redact-sensitive`
: Redact sensitive values in debug diagnostics (default: enabled).

`--no-debug-info-redact-sensitive`
: Disable sensitive-value redaction in debug diagnostics.

## Debug Info Output

By default, debug info is written to:

`./.scadview/debug_info.json`

SCADview keeps a small rotation of previous runs:

- `debug_info.1.json`
- `debug_info.2.json`
- ...
- up to `debug_info.5.json`

## Environment Variables

`SCADVIEW_DEBUG_INFO_FILE`
: Same as `--debug-info-file`.

`SCADVIEW_DEBUG_INFO_REDACT_SENSITIVE`
: Control path redaction behavior in debug info.
: Accepted values: `1|true|yes|on` or `0|false|no|off` (default: redaction enabled).

## Examples

```bash
python -m scadview -v
python -m scadview -vv
python -m scadview --log-level ERROR
python -m scadview --debug-info-file /tmp/scadview-debug.json
python -m scadview --no-debug-info-redact-sensitive
SCADVIEW_DEBUG_INFO_REDACT_SENSITIVE=false python -m scadview
```
