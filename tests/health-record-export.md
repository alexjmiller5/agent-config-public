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
