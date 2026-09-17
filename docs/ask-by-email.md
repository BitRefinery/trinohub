# Ask by email

Email a question to your TrinoHub inbound address — for example *"What were
net sales yesterday?"* — and get the answer back as a reply. No sign-in, no
SQL. Replies arrive from the same thread, so you can follow up with *"And the
day before?"*.

## What you get back

Every reply has:

- **The answer**, with the date range the data covers and any assumption made
  (for example what "sales" was taken to mean).
- **How it was answered:**
  - *Vetted query template* — a curated query your data team published for this
    kind of question. Treat it like a report.
  - *Freeform draft* — no template fit, so the assistant wrote its own read-only
    query. Treat the number as a best read and check it before relying on it.
- **Links to the queries** in **Query history**, so anyone with access can see
  exactly where a number came from.

## Replying to a digest

If you receive a scheduled digest by email, reply to it with a follow-up
question. The assistant sees the digest you are replying to, so *"why is that
number down?"* works without restating it. Only the digest's own recipient gets
that context — a forwarded digest is answered as a fresh question.

## Whose data you see

The assistant acts **as you**. It can only query what your TrinoHub account can
query, and data policies such as row filters apply exactly as they do in the SQL
editor — a store manager asking about sales sees their own store. It can never
change data.

## Who can ask

Your administrator enables this per role with the `ASK_BY_EMAIL` privilege.
Email must come from the address on your TrinoHub account, and your mail
provider must pass sender authentication (DMARC). Mail that fails those checks
is dropped without a reply. Each person can ask up to 20 questions an hour.

If you get *"This address isn't set up to answer questions from you"*, ask an
administrator to add your email address to your account and your account to a
role with `ASK_BY_EMAIL`.

## Setting it up (administrators)

Answering email builds on outbound email (see **Settings & security → Email**)
and the Ask Trino model configuration (`OPENROUTER_API_KEY`; the model chosen in
**Settings → Ask Trino** must support tool calling).

1. **Deploy the email stack.** `deploy/aws/email-front-door.yaml` creates
   everything on the AWS side in one go: the SES domain identity, the receipt
   rule for the inbound address, the SNS topic and SQS queue, and the
   control-plane role's send/receive permissions. Deploy it in a
   [region where SES receives email](https://docs.aws.amazon.com/ses/latest/dg/regions.html#region-receive-email)
   (see `deploy/aws/README.md → Email front door`). Doing it by hand instead:
   verify the domain, add a receipt rule with an **SNS action** (encoding UTF-8;
   SNS actions carry messages up to 150 KB) to a topic subscribed by an SQS
   queue named `trinohub-inbound*`, and grant the control-plane role
   `ses:SendEmail`, `sqs:ReceiveMessage` and `sqs:DeleteMessage`.
2. **Publish DNS and activate.** Add the stack's DKIM CNAME and MX records to
   your DNS, run its `ActivateRuleSet` command once, and — if the account is in
   the SES sandbox — request production access.
3. **Set the email region.** In **Settings → Email**, set **SES region** to the
   stack's region if it differs from the control plane's.
4. **Turn it on** in **Settings → Email**: tick **Answer emailed questions**
   and enter the inbound address and the queue URL.
5. **Grant access**: create or edit a role with `ASK_BY_EMAIL` and put people
   in it. Make sure each person's account has their email address.
6. **Curate answers**: publish query templates for the questions people ask
   most (see **Data products & query templates**). The assistant always looks
   for a data product and a template before writing its own SQL.

Every inbound email — answered, refused, or rejected — is listed under
**Settings → Emailed questions** and recorded in the security audit log.
