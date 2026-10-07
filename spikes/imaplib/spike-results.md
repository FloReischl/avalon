# IMAP Spike Results

## Scope

This spike investigated direct mail access for Avalon using Python's standard
`imaplib`.

Tested providers:

- mailbox.org using IMAP username/password authentication
- Gmail using OAuth2/XOAUTH2

The spike focused on reading mail and investigating provider-specific tagging
and label semantics. Sending mail via SMTP was not investigated.

## General IMAP

Python's standard `imaplib` is sufficient for the IMAP operations investigated
in this spike.

Mail headers and bodies can be fetched without marking messages as read by
using `BODY.PEEK[...]`.

Provider-specific authentication and mailbox semantics differ enough that they
must not be assumed to be portable merely because both providers expose IMAP.

## mailbox.org

### Authentication and reading

Direct IMAP access using username/password authentication works.

The spike successfully:

- connected using IMAP over SSL
- selected `INBOX`
- listed messages
- fetched headers
- fetched complete message bodies without intentionally changing read state

### Tags and categories

mailbox.org does not expose a Gmail-equivalent arbitrary label model through
its web UI.

IMAP itself supports flags/keywords, and clients such as Thunderbird can use
IMAP keywords for tags. However, mailbox.org Webmail has its own category and
colored-flag concepts.

These mechanisms do not form one clearly interoperable tagging model across
mailbox.org Webmail, Thunderbird and generic IMAP clients.

For Avalon, mailbox.org tagging was therefore not pursued further in this
spike.

No conclusion was reached that mailbox.org cannot technically store useful
IMAP keywords. The result is only that relying on them as a user-visible,
provider-independent label model would require additional investigation.

## Gmail

### OAuth2

Gmail IMAP access works using OAuth2/XOAUTH2.

The tested setup uses:

- a Google Cloud OAuth client of type `Desktop app`
- OAuth scope `https://mail.google.com/`
- interactive browser consent for the initial authorization
- a persisted user token for subsequent runs
- XOAUTH2 authentication against `imap.gmail.com`

The OAuth client configuration identifies the application. The persisted user
token represents the user's authorization and contains the information needed
to obtain fresh access tokens without repeating interactive consent on every
run.

The spike stores the token under:

`~/.avalon/security/gmail-token.json`

with file mode `0600`.

The Google OAuth client configuration is currently supplied through the
environment variable:

`AVALON_GMAIL_CLIENT_SECRET`

The Gmail account is supplied through:

`AVALON_GMAIL_USER`

### Gmail IMAP extensions

The tested Gmail account advertises the capability:

`X-GM-EXT-1`

The spike successfully used Gmail's IMAP extensions:

- `X-GM-MSGID`
- `X-GM-LABELS`
- `+X-GM-LABELS`
- `-X-GM-LABELS`
- `SEARCH X-GM-MSGID`

`X-GM-MSGID` provides a stable Gmail message identifier that can be used to
find the same physical message after switching IMAP mailboxes.

### Gmail label semantics

Gmail custom labels are represented as IMAP mailboxes for selection purposes.

A test message carrying the custom hierarchical label:

`Avalon/Test`

could be found by selecting that mailbox.

An important observed behavior is that `X-GM-LABELS` depends on the selected
IMAP mailbox.

For the same physical message, verified using the same `X-GM-MSGID`:

- when `Avalon/Test` was selected, `X-GM-LABELS` returned an empty label list
- when Gmail's All Mail mailbox was selected, `X-GM-LABELS` returned
  `Avalon/Test`

Therefore Avalon must not assume that fetching `X-GM-LABELS` from an arbitrary
selected label mailbox returns the complete Gmail label set.

For the behavior tested here, Gmail's All Mail mailbox provides the reliable
view for reading and manipulating complete custom-label metadata.

### Multiple and hierarchical custom labels

A second custom label was created:

`Avalon/Test2`

The spike selected a message through `Avalon/Test`, located the same message in
All Mail using `X-GM-MSGID`, and added `Avalon/Test2` using `+X-GM-LABELS`.

The subsequent readback showed both custom labels on the same message:

- `Avalon/Test`
- `Avalon/Test2`

This verifies for the tested account that:

- one Gmail message can carry multiple custom labels
- hierarchical custom labels containing `/` work through the Gmail IMAP
  extension
- labels can be added individually
- labels can be removed individually without removing another custom label

The test then removed `Avalon/Test2` using `-X-GM-LABELS` and verified that
`Avalon/Test` remained present.

The test also performs cleanup in `finally` so that `Avalon/Test2` is removed
even if an assertion fails after the label has been added.

### All Mail discovery

The Gmail All Mail mailbox name is localized.

For the tested German account it is:

`[Gmail]/Alle Nachrichten`

Hardcoding `[Gmail]/All Mail` or the German name is therefore not portable.

Gmail exposes the semantic special-use flag `\All` in the IMAP `LIST`
response. The spike discovers the All Mail mailbox by this flag instead of by
its localized name.

For the tested account, the relevant `LIST` entry was equivalent to:

`(\All \HasNoChildren) "/" "[Gmail]/Alle Nachrichten"`

Avalon should use the semantic `\All` flag when it needs Gmail's All Mail
mailbox.

## Conclusions for Avalon

The spike establishes that direct IMAP access is technically viable for the
investigated read use cases.

Gmail additionally provides a usable n:m custom-label model through its IMAP
extensions. Complete Gmail label metadata should be handled from the mailbox
identified by the `\All` special-use flag rather than relying on the currently
selected custom-label mailbox.

mailbox.org reading works, but no equivalent interoperable user-facing tagging
model was established.

These are spike findings, not an architectural decision. Provider abstraction,
production credential handling, mail synchronization strategy, error handling,
and the final Avalon mail capability/API remain deliberately undecided.

## Not investigated

The spike did not establish behavior for:

- SMTP or sending mail
- deleting or moving mail
- changing read/unread state
- attachments as a dedicated use case
- incremental synchronization
- reconnect and retry behavior
- OAuth token revocation or recovery
- concurrent access
- production secret storage
- Gmail API access as an alternative to IMAP
- portable tag semantics across providers