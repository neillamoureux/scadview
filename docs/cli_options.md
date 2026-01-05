# Command-Line Options

Run SCADview from the command line with:

```bash
python -m scadview
```

The launcher only accepts logging-related options. Use these when you need
more or less console output while the UI runs.

## Options

`-v`, `--verbose`
: Increase verbosity. Use `-v` for INFO or `-vv` for DEBUG.

`--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`
: Set the logging level directly. This overrides `-v`/`-vv` when provided.

## Examples

```bash
python -m scadview -v
python -m scadview -vv
python -m scadview --log-level ERROR
```
