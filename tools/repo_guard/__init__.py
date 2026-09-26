"""Repository guard.

Blocks commits and pushes that would publish sensitive data: credentials,
payment gateway and SMS panel keys, trust seal codes, contact details,
customer or seller records, database dumps and backups.

Run ``python -m tools.repo_guard --help`` for the available commands.
"""

__version__ = "1.0.0"
