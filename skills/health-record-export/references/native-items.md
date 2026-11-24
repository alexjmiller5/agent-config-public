# Native item mechanics

Discover current support rather than relying on an old category list:

```sh
op item template list --format json
op item template get 'Medical Record' --format json
op item create --help
op document create --help
```

The Medical Record template provides date, location, healthcare professional,
patient, reason for visit, medication, dosage, medication notes and general
notes. Use the returned field and section IDs. Readback must report
`MEDICAL_RECORD`. If the installed CLI does not support it, use the supported
1Password app interface rather than substituting a Secure Note silently.

Put clinical values in JSON passed through stdin. A file assignment attaches
the original directly to the native item:

```sh
op item create --vault '<vault-id>' - 'Source[file]=<original-path>'
op document create '<archive-path>' --vault '<vault-id>' \
  --title '<approved-title>' --tags '<approved-tags>' --format json
```

For item JSON, carry approved tags and fields for the source record ID,
original source date/status, source SHA-256 and original archive item ID.
Record item and file IDs returned by creation. Separate prescription orders,
dispensing and administrations; keep exact directions without inferring a
clinical dose. An export date is not an encounter date. Leave unavailable
clinical dates unset and label their absence.

Match a diagnostic report's results only to Observation IDs from the same
source. Group remaining observations by source, encounter, clinical date and
category according to the approved format. Retain raw FHIR for every grouped
record and reconcile the set of covered source IDs with the input inventory.
Patient/demographic resources and references without bodies must also be
accounted for, even when they remain only in the original archive.

Verify saved fields and attachment bytes:

```sh
op item get '<item-id>' --vault '<vault-id>' --format json
op read --no-newline 'op://<vault-id>/<item-id>/<file-id>'
op document get '<document-id>' --vault '<vault-id>'
```

Pipe downloaded bytes into a hash computation, never into the transcript.
`op read` adds a newline unless `--no-newline` is supplied, which otherwise
breaks byte comparisons. Check command exit status as well as hashes. Keep
the original source record after a failed import. A 409 conflict is not proof
that a write created nothing: inspect matching source IDs before retrying.

Check current [file limits](https://support.1password.com/files/) and available
capacity before large imaging archives. Return actual sizes and options if
the requested destination cannot hold them. Current vendor references:
[item categories](https://support.1password.com/item-categories/),
[CLI item commands](https://www.1password.dev/cli/reference/management-commands/item),
[Epic record sharing](https://www.mychart.org/l/en-us/features/share/),
[Apple export](https://support.apple.com/en-ie/guide/iphone/iph5ede58c3d/ios),
[Apple medication list and logs](https://support.apple.com/en-us/105064).

## When the Apple export lacks dose history

The HealthKit medication APIs on supported systems distinguish user-tracked
medications and dose events from provider prescriptions. A reader must have
permission for each relevant medication, including archived medications and
new ones added since the last export. See Apple's
[medication API introduction](https://developer.apple.com/videos/play/wwdc2025/321/).

Prefer a supported existing exporter before proposing a new app. Health Auto
Export documents iPhone/iPad Manual Export with **Medications**, a selected
date range and JSON Version 2. Its
[medication schema](https://help.healthyapps.dev/en/health-auto-export/export-format/medications/)
includes dose status, timestamps, quantities and units. Its
[manual export instructions](https://help.healthyapps.dev/en/health-auto-export/manual-export/)
are distinct from its Mac export, which documents metrics and workouts.
Confirm the user's app choice, any cost, permissions and delivery destination
before setup. A manual local export does not need the vendor's email delivery.

Compare oldest/newest dates and representative Taken/Skipped events with the
Health app. Keep other source statuses distinct; missing permission or an
unlogged event is not proof that a dose was skipped. The documented exporter
schema omits some raw HealthKit metadata, including event UUID and schedule
type, and does not guarantee complete historical backfill. State that limit
if the user requests every underlying field.

## Separate My Documents files

Open the confirmed institution's **Document Center > My Documents** in an owned
browser tab, verify the patient/profile, and obtain that exact CDP target ID.
With Node 22+ and `uv` available:

```sh
uv run scripts/mychart_documents.py --port <local-or-forwarded-CDP-port> \
  --target '<owned-target-id>' --source '<confirmed-institution-label>' \
  --out-dir '<private-temporary-directory>'
```

The helper reads the identified tab's session into memory, then uses the
portal's observed `LoadOtherDocuments` and `GetDocumentDetails` retrieval
endpoints. It follows the supplied download URL only within the same HTTPS
origin. It neither signs documents nor submits record requests. It fails on
expired sessions, malformed responses, repeated pagination and unexpected
authentication HTML. Existing originals and completed receipts survive a
partial failure; retry only after inspecting the cause.

Compare the completed count with the fully expanded UI list. The private
`manifest.jsonl` retains source metadata, identifiers, file paths, sizes and
SHA-256 hashes. Upload originals with meaningful approved titles and filenames,
verify them in 1Password, and retain the manifest in the user's export register.
Encrypted portal IDs can depend on the session: reenumerate next time and use
hashes and clinical provenance as well as identifiers for reconciliation.
