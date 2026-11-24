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
