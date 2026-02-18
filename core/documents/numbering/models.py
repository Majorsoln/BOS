"""
BOS Documents - Numbering Engine Models
=========================================
Defines the NumberingPolicy dataclass: the configuration for document numbering.

Doctrine:
- Same policy + sequence position → same document number (deterministic).
- Numbering is event-driven: sequence advances by counting issued documents.
- No random() or current time inside number generation logic.
- Fiscal reset period is resolved from explicit datetime arguments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Reset period identifiers
# ---------------------------------------------------------------------------

RESET_NEVER = "NEVER"        # Sequence never resets
RESET_DAILY = "DAILY"        # Resets at start of each calendar day
RESET_MONTHLY = "MONTHLY"    # Resets at start of each calendar month
RESET_YEARLY = "YEARLY"      # Resets at start of each calendar year

VALID_RESET_PERIODS = frozenset({RESET_NEVER, RESET_DAILY, RESET_MONTHLY, RESET_YEARLY})

# ---------------------------------------------------------------------------
# NumberingPolicy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NumberingPolicy:
    """
    Declares how document numbers are formatted and sequenced.

    Fields:
        policy_id: unique identifier for this policy
        business_id_str: the business this policy belongs to (str form of UUID)
        doc_type: e.g. "RECEIPT", "INVOICE", "QUOTE"
        prefix: prepended before the sequence (e.g. "RCP-", "INV-")
        suffix: appended after the sequence (e.g. "/2026")
        padding: minimum digit width for the sequence number (e.g. 5 → "00001")
        reset_period: when the sequence counter resets (NEVER/DAILY/MONTHLY/YEARLY)
        branch_id_str: optional — if set, applies only to this branch
        start_at: starting sequence number (default 1)
    """
    policy_id: str
    business_id_str: str
    doc_type: str
    prefix: str = ""
    suffix: str = ""
    padding: int = 5
    reset_period: str = RESET_NEVER
    branch_id_str: Optional[str] = None
    start_at: int = 1

    def __post_init__(self):
        if not self.policy_id or not isinstance(self.policy_id, str):
            raise ValueError("policy_id must be a non-empty string.")
        if not self.business_id_str or not isinstance(self.business_id_str, str):
            raise ValueError("business_id_str must be a non-empty string.")
        if not self.doc_type or not isinstance(self.doc_type, str):
            raise ValueError("doc_type must be a non-empty string.")
        if not isinstance(self.prefix, str):
            raise ValueError("prefix must be a string.")
        if not isinstance(self.suffix, str):
            raise ValueError("suffix must be a string.")
        if not isinstance(self.padding, int) or self.padding < 1:
            raise ValueError("padding must be int >= 1.")
        if self.reset_period not in VALID_RESET_PERIODS:
            raise ValueError(
                f"reset_period '{self.reset_period}' is not valid. "
                f"Must be one of: {sorted(VALID_RESET_PERIODS)}"
            )
        if self.branch_id_str is not None and not isinstance(self.branch_id_str, str):
            raise ValueError("branch_id_str must be string or None.")
        if not isinstance(self.start_at, int) or self.start_at < 1:
            raise ValueError("start_at must be int >= 1.")

    def format_number(self, sequence: int) -> str:
        """
        Format a document number from a sequence position.

        Args:
            sequence: the 1-based sequence count (>= start_at)

        Returns:
            e.g. "INV-00042/2026"
        """
        if not isinstance(sequence, int) or sequence < 1:
            raise ValueError("sequence must be int >= 1.")
        padded = str(sequence).zfill(self.padding)
        return f"{self.prefix}{padded}{self.suffix}"
