# Python environments managed by uv

The two virtual environments found under this repository have been migrated to
uv projects. Other folders containing Python scripts have not been changed.

| Project | Python | Previous environment (retained) | Active environment |
| --- | --- | --- | --- |
| `2026-06-16-spacexperps` | 3.13 | `venv/` | `.venv/` |
| `2026-11-10-etf_flows_bbg` | 3.11 | `.venv-before-uv/` | `.venv/` |

Each project contains:

- `pyproject.toml`: direct dependencies pinned to their previously installed versions.
- `.python-version`: Python minor version used by uv.
- `uv.lock`: resolved dependencies for reproducible installs.
- `requirements-before-uv.txt`: full snapshot of the original environment.

Transitive dependencies were resolved afresh and may differ from the snapshots.
The original environments are retained for rollback; do not delete them until
normal reports/data pulls have been checked.

## Usage

From either project directory:

```powershell
uv sync --locked
uv run python <script_name>.py
uv add <package>
uv remove <package>
```

No activation or manual pip installation is needed. Commit `pyproject.toml`,
`.python-version`, and `uv.lock` when dependencies change. Environment directories
are ignored by Git.

For example, from the repository root:

```powershell
uv run --project ./2026-06-16-spacexperps python ./2026-06-16-spacexperps/generate_report.py
./2026-11-10-etf_flows_bbg/pull_command.ps1
```

Some SpaceX scripts use working-directory-relative paths; run them from their
project directory to keep inputs and outputs in the expected location.
The ETF PowerShell launcher sets the project working directory automatically and
forwards arguments to `pull_etf_data.py`.

## Bloomberg requirements

`blpapi` is sourced explicitly from Bloomberg's official Python package index;
other packages use the default index. The project retains Python 3.11, matching
the previous x64 environment. Real data pulls still require a logged-in Bloomberg
Terminal and the Bloomberg runtime/API connection.

## Verification and rollback

Dependency imports passed in both new environments, including `blpapi` and
`from xbbg import blp`. The ETF CLI help also passed. No network data pulls or
report generation were run during migration.

For rollback, stop any processes using the environments first. SpaceX's original
`venv` can still be used directly. For ETF, move the new `.venv` out of the way
and rename `.venv-before-uv` back to `.venv` before using it; activation scripts
in the backup still refer to the original path. The former ETF launch command was
`.\.venv\Scripts\python.exe .\pull_etf_data.py` from its project directory.

If uv warns that `VIRTUAL_ENV` points to another environment, run `deactivate`
in that shell first. uv uses the project `.venv` by default; do not use `--active`
unless you deliberately want to modify the unrelated activated environment.
