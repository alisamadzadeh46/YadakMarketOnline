# YadakMarket Online

An online marketplace for automotive spare parts, connecting buyers with parts sellers.

## Getting started

```bash
git clone https://github.com/alisamadzadeh46/YadakMarketOnline.git
cd YadakMarketOnline

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env                    # then fill in the real values
python -m tools.repo_guard install-hooks
```

Python 3.9 or newer is required.

## Configuration

Every credential and every deployment specific value is read from environment
variables, loaded from a local `.env` file. `.env` is git-ignored; `.env.example`
documents the available variables with empty or placeholder values.

| Group          | Variables                                              |
| -------------- | ------------------------------------------------------ |
| Core           | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` |
| Database       | `DB_*`                                                 |
| Payment        | `ZARINPAL_MERCHANT_ID`, `ZARINPAL_SANDBOX`, `ZARINPAL_CALLBACK_URL` |
| SMS panel      | `SMS_*`                                                |
| Trust seals    | `ENAMAD_ID`, `ENAMAD_CODE`, `SAMANDEHI_ID`             |
| Contact info   | `CONTACT_*`                                            |
| E-mail         | `EMAIL_*`, `DEFAULT_FROM_EMAIL`                        |
| Deployment     | `DEPLOY_*`                                             |

Business data such as seller profiles, addresses and phone numbers is stored in
the database and is never part of the source code, fixtures or migrations.

## Protecting sensitive data

The repository is public. The following must never be committed:

- `.env` files, credentials, API keys, private keys and certificates
- payment gateway (ZarinPal) merchant IDs and SMS panel keys or passwords
- eNamad / Samandehi seal IDs and codes
- real phone numbers, e-mail addresses, postal addresses and server addresses
- database files, dumps, data exports and backups
- uploaded media (product photos, seller documents)
- personal data of customers and sellers (national IDs, card and Sheba numbers)

### How it is enforced

1. **`.gitignore`** keeps the usual sensitive files out of `git add`.
2. **Git hooks** in `.githooks/`, enabled with `python -m tools.repo_guard install-hooks`:
   - `pre-commit` scans staged files and content,
   - `commit-msg` scans the commit message,
   - `pre-push` re-scans every commit that is about to be pushed.
3. **CI** (`.github/workflows/repo-guard.yml`) runs the same checks on every push and pull request.

The hooks look for Python in `venv/` or `.venv/` inside the repository, then
on the `PATH`. When neither works (for example a broken `python` alias on
Windows), point them to an interpreter explicitly:

```bash
git config repo-guard.python "C:/path/to/python.exe"
```

The rules live in `tools/repo_guard/rules.py`. Each rule is a small declarative
object, so new checks are added by appending to `PATH_RULES` or `CONTENT_RULES`.

### Project specific values

Generic patterns cannot recognise a shop name or a street address. List such
values, one per line, in `.repo-guard.local` at the repository root. The file is
git-ignored and is read only on your machine:

```text
# Real values that must never appear in the repository
<shop phone number>
<shop address>
<server IP address>
<ZarinPal merchant ID>
<SMS panel API key>
<seller or shop names>
```

Numbers match regardless of spacing, dashes, Persian digits or a `+98` prefix;
text matches case-insensitively.

### Importing existing code

To publish code that was written before the guard existed, copy it into a
clone of this repository and run:

```bash
python -m tools.repo_guard prepare
```

The command shows a plan and applies it only after confirmation:

- sensitive values are replaced with `__REDACTED__` in place, and the original
  values are saved to `.redactions.local` (git-ignored) for moving into `.env`;
- files that must not be published, and data files such as fixtures or CSV
  exports, are held back for manual review;
- virtual environments that `.gitignore` does not cover are excluded;
- everything else is staged, ready for `git commit` and `git push`.

### Useful commands

```bash
python -m tools.repo_guard all            # audit every file that would be committed
python -m tools.repo_guard history        # audit every commit in the local history
python -m tools.repo_guard range main..HEAD
python -m unittest discover -s tools -t . # run the guard test suite
```

For a verified false positive, add a comment containing `repo-guard: allow` to
the affected line. Never bypass the hooks with `--no-verify`.

### If something leaks

1. Revoke or rotate the exposed value first (merchant key, SMS key, server
   password, secret key). Rewriting history does not remove copies that were
   already fetched or cached.
2. Remove the value from the code and load it from `.env`.
3. Rewrite the affected commits before pushing again.

## Development conventions

- Code follows PEP 8 and is checked with [Ruff](https://docs.astral.sh/ruff/)
  (`ruff check .` and `ruff format .`, configured in `ruff.toml`).
- Code, comments and docstrings are written in English. Comments explain *why*
  something is done; the code itself should make *what* obvious.
- Configuration comes from the environment; business data comes from the database.
- Every change is covered by tests where practical.
