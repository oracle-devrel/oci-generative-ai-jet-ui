"""Short AML policy and typology notes for the Meridian Bank knowledge store (Part 3).

Each note is (subject, body). The thresholds match the Part 6 triage policy: $10,000 is the
currency transaction report (CTR) line and $50,000 needs a source-of-funds note.
"""

AML_NOTES = [
    ("AML_POLICY.CTR_THRESHOLD",
     "Cash transactions above $10,000 in one business day trigger a currency transaction report "
     "(CTR). The report is filed automatically; no analyst decision is needed."),
    ("AML_POLICY.SOURCE_OF_FUNDS",
     "A single cash deposit above $50,000 needs a documented source-of-funds note before the "
     "alert can be closed as legitimate."),
    ("AML_TYPOLOGY.STRUCTURING",
     "Structuring (smurfing): a customer splits cash deposits into amounts just under the "
     "$10,000 CTR threshold, often across several days or branches, to avoid the report."),
    ("AML_TYPOLOGY.RAPID_MOVEMENT",
     "Rapid in-out movement: funds arrive and leave the account within hours or a day, leaving "
     "a near-zero balance. The account is used as a pass-through, not for saving or spending."),
    ("AML_TYPOLOGY.CASH_OUT_AFTER_WIRE",
     "Cash-out after inbound wire: a large incoming wire is followed by cash withdrawals or ATM "
     "draws that drain most of it within a few days."),
    ("AML_TYPOLOGY.LAYERING",
     "Layering: money moves through a chain of accounts or merchants with no business purpose, "
     "so the original source becomes hard to trace."),
    ("AML_TYPOLOGY.ROUND_AMOUNTS",
     "Repeated round-number transfers (for example exactly $9,500 or $9,900) are a common "
     "structuring signal and deserve review even when each one is small."),
    ("AML_TYPOLOGY.DORMANT_ACTIVATION",
     "A dormant account that suddenly receives and sends large amounts is suspicious, "
     "especially when the account holder profile shows little income."),
    ("AML_TYPOLOGY.HIGH_RISK_JURISDICTION",
     "Transfers to or from jurisdictions on the high-risk list need enhanced due diligence, "
     "whatever the amount."),
    ("AML_TYPOLOGY.SHELL_MERCHANT",
     "Shell merchants: a merchant with a high card volume, few distinct customers and no "
     "physical location can be used to launder card payments."),
    ("AML_TYPOLOGY.GEOGRAPHIC_ANOMALY",
     "Impossible travel: login or card activity in two distant cities within a window too "
     "short to travel suggests a compromised account or a shared credential."),
    ("AML_POLICY.KYC_REFRESH",
     "Customers rated high risk (risk rating above 70) get a KYC refresh every 12 months; "
     "other customers every 36 months. Expired documents block new account types."),
    ("AML_POLICY.PEP",
     "Politically exposed persons (PEPs) and their close associates need senior management "
     "approval to open an account and are screened on every large transaction."),
    ("AML_POLICY.SAR_FILING",
     "A suspicious activity report (SAR) is filed within 30 days of detecting suspicious "
     "activity. The narrative states who, what, when, where and why. Do not tip off the customer."),
    ("AML_POLICY.ALERT_DISPOSITION",
     "Every alert ends in one of three dispositions: escalate (file a SAR), request more "
     "information, or close as a false positive. Each decision needs a written rationale."),
    ("AML_POLICY.EVIDENCE_STANDARD",
     "An escalation must cite concrete evidence: transaction ids, amounts, dates and the rule "
     "that fired. A closure must say which evidence cleared the alert."),
    ("AML_POLICY.VELOCITY_LIMITS",
     "Velocity rules flag more than 5 cash transactions, or more than $25,000 in total, in "
     "any rolling 7 days on a retail account."),
    ("AML_POLICY.WIRE_REVIEW",
     "International wires above $10,000 are screened against sanctions lists before release. "
     "A hit freezes the wire and goes to the sanctions team."),
    ("AML_POLICY.RECORD_RETENTION",
     "AML records, including alert decisions and their rationale, are kept for five years "
     "after the account closes."),
    ("AML_POLICY.FALSE_POSITIVES",
     "Payroll deposits, rent and recurring bill payments with a stable amount and a known "
     "counterparty are usually false positives. Close them with a short note."),
]
