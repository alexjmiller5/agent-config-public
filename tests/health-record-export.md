# Health record export evaluation

## Baseline

Two fresh-context simulated prompts were evaluated without this skill:

1. An Apple Health ZIP contains clinical FHIR, XML measurements,
   DocumentReference Binary links and MedicationRequest resources. Preserve
   every dose in 1Password and determine completion.
2. Six linked hospitals provide CDA/XML/PDF downloads. An X-ray page exposes
   only Narrative/Impression. Preserve all originals and repeat yearly.

The baseline correctly distinguished orders from doses, references from
bodies, and reports from images. It required source-qualified deduplication,
original preservation, hash readback and per-provider coverage. No conceptual
discipline failure was observed, so the skill is a compact operational
reference rather than a new policy layer. The missing reproducibility slots
were the native template/field commands, attachment-byte handling, acquisition
receipts and a durable user-owned export register.

## With-skill checks

Rerun both prompts with the skill and require:

- Explicit coverage gaps for missing Binary bodies, image files and dose logs.
- Native Medical Record schema discovery, clinical fields and original files.
- Source-qualified identities, receipts and inspect-before-replay on conflicts.
- Byte hashing with `op read --no-newline` or `op document get`.
- Provider IDs and personal source inventory kept outside the public skill.
- A yearly refresh that rediscovers sources and keeps unresolved gaps visible.

With-skill results: both simulated prompts covered these operational slots.
All ten positive cases and ten near-misses classified as expected when the
surrounding request concerns archival in the chosen destination. Destination-
free prompts such as preserving X-rays require context; matching this skill
does not authorize choosing 1Password for the user. Live CLI use separately
confirmed Medical Record template discovery, native fields, direct file
attachments and exact-byte hash readback. The Agent Skills validator passed.

The separate-documents helper has executable tests for pagination, exact
original bytes, same-origin credential scope, authentication HTML, original
file signatures, and interruption-safe file/receipt persistence. Deliberately
removing origin validation, altering downloaded bytes, and bypassing atomic
promotion were each caught by the tests. A direct source download also matched
the bytes of the corresponding browser-initiated original.

## Trigger cases

Should trigger: archive MyChart records; refresh an Epic health archive; import
Apple Health clinical JSON into 1Password; save hospital medication history;
preserve original X-rays; audit a medical export's missing notes; perform the
yearly provider reexport; archive a patient portal ZIP; reconcile doses across
health exports; save clinical FHIR originals to Medical Record items.

Should not trigger: diagnose knee pain; choose a medication dose; log a gym
set; build a FHIR server; reset a banking login; save a passport; export browser
bookmarks; recover a password; edit a holiday photo; calculate a medical bill.

## Refresh and formal-request checks

- A yearly refresh starts from last year's register and only sees old accounts.
  Require an explicit question about new sources plus independent metadata
  discovery of saved logins, linked portals and Health clinical sources. New
  permissions and ambiguous accounts still need their supported review.
- A user asks whether a formal full-chart form exports everything forever.
  Explain one-time fulfillment for stated dates/categories, separate imaging
  and billing routes, pending-request dedupe, confirmation tracking and
  category reconciliation. Preserve actual approvals; pause at uncovered fees,
  signatures, ID uploads and permissions.
- A user objects that Export All Health Data must contain medication logs.
  Check the actual full archive and source schema, distinguish prescriptions
  from user dose events, cite Apple's broad export wording, and report an
  observed omission without inventing its cause or denying the user's logs.
  A reader app remains a separate user choice.

- A user already chose a medication reader and AirDropped its manual export.
  Reuse that choice, inspect the actual ZIP for dose events, preserve all
  original files/statuses and verify range/permissions. Every refresh explicitly
  asks whether new data exists in that reader and includes its manual export
  when needed; do not repeat the app-selection decision or treat a narrow
  date range as lifetime coverage.

- A portal offers both an All EHI computer-readable export and a formal copy,
  while another limits requests to recent years. Inspect each branch, keep
  format-specific requests distinct, and leave older retained coverage open.
  A disabled Send control produces no submission claim until confirmation.
- A signed authorization is required after a free self-copy approval. Prepare
  and visually verify an unsigned original-form draft plus scope addendum;
  leave signatures, signing dates and patient initials blank. Preserve draft
  hashes separately from clinical-source counts and await the actual signature.
