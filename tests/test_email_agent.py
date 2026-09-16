import base64
import json
import tempfile
import unittest
from pathlib import Path

from trinohub import email_agent
from trinohub.server import ApiError, TrinoHubApp

from test_server import FakeAws


def raw_email(
    *,
    sender="Dana Store <dana@example.com>",
    subject="Sales yesterday?",
    body="What were net sales yesterday?\n\nOn Mon, Sep 15, 2026 at 7:00 AM TrinoHub wrote:\n> old answer",
    message_id="<q1@mail.example.com>",
    extra_headers="",
):
    return (
        f"From: {sender}\r\nTo: ask@trinohub.example.com\r\nSubject: {subject}\r\n"
        f"Message-ID: {message_id}\r\n{extra_headers}MIME-Version: 1.0\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n\r\n" + body.replace("\n", "\r\n")
    )


def ses_notification(raw, *, ses_id="ses-1", verdicts=None, wrap_sns=True, base64_encoded=False):
    verdicts = {"spf": "PASS", "dkim": "PASS", "dmarc": "PASS", "spam": "PASS", "virus": "PASS", **(verdicts or {})}
    payload = {
        "notificationType": "Received",
        "mail": {"messageId": ses_id, "source": "dana@example.com"},
        "receipt": {
            "recipients": ["ask@trinohub.example.com"],
            "action": {"type": "SNS", "encoding": "BASE64" if base64_encoded else "UTF8"},
            **{f"{name}Verdict": {"status": status} for name, status in verdicts.items()},
        },
        "content": base64.b64encode(raw.encode()).decode() if base64_encoded else raw,
    }
    if not wrap_sns:
        return json.dumps(payload)
    return json.dumps({"Type": "Notification", "Message": json.dumps(payload)})


class ParsingTests(unittest.TestCase):
    def test_sns_wrapped_notification_extracts_question_and_threading(self):
        inbound = email_agent.parse_ses_notification(
            ses_notification(
                raw_email(extra_headers="In-Reply-To: <a@x>\r\nReferences: <root@x> <a@x>\r\n")
            )
        )
        self.assertEqual(inbound.ses_message_id, "ses-1")
        self.assertEqual(inbound.from_address, "dana@example.com")
        self.assertEqual(inbound.question, "What were net sales yesterday?")
        self.assertEqual(inbound.message_id, "<q1@mail.example.com>")
        self.assertEqual(inbound.references, ["<root@x>", "<a@x>"])
        self.assertEqual(inbound.in_reply_to, "<a@x>")
        self.assertFalse(inbound.automated)
        self.assertEqual(inbound.verdicts["dmarc"], "PASS")

    def test_raw_delivery_and_base64_content(self):
        inbound = email_agent.parse_ses_notification(
            ses_notification(raw_email(body="Top 5 stores this week?"), wrap_sns=False, base64_encoded=True)
        )
        self.assertEqual(inbound.question, "Top 5 stores this week?")

    def test_html_only_body_and_quote_markers(self):
        raw = (
            "From: dana@example.com\r\nSubject: q\r\nMessage-ID: <h@x>\r\nMIME-Version: 1.0\r\n"
            "Content-Type: text/html; charset=utf-8\r\n\r\n"
            "<div>Margin by store&nbsp;last month?</div><div>-----Original Message-----</div><div>secret</div>"
        )
        inbound = email_agent.parse_ses_notification(ses_notification(raw))
        self.assertIn("Margin by store", inbound.question)
        self.assertNotIn("secret", inbound.question)

    def test_automated_mail_is_flagged(self):
        for header in ("Auto-Submitted: auto-replied\r\n", "Precedence: bulk\r\n", "List-Id: <x.y>\r\n"):
            inbound = email_agent.parse_ses_notification(ses_notification(raw_email(extra_headers=header)))
            self.assertTrue(inbound.automated, header)

    def test_rejects_non_ses_messages(self):
        for body in ("not json", json.dumps({"notificationType": "Bounce"}), json.dumps({"Type": "Notification", "Message": "{}"})):
            with self.assertRaises(email_agent.InboundParseError):
                email_agent.parse_ses_notification(body)

    def test_sender_authentication(self):
        passing = {"spf": "PASS", "dkim": "PASS", "dmarc": "PASS", "spam": "PASS", "virus": "PASS"}
        self.assertEqual(email_agent.sender_authenticated(passing), (True, ""))
        self.assertTrue(email_agent.sender_authenticated({**passing, "spf": "FAIL"})[0])
        for change in ({"dmarc": "FAIL"}, {"dmarc": "GRAY"}, {"dkim": "FAIL", "spf": "FAIL"}, {"virus": "FAIL"}, {"spam": "FAIL"}):
            self.assertFalse(email_agent.sender_authenticated({**passing, **change})[0], change)


def tool_call(name, arguments, call_id="c1"):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}


class AgentLoopTests(unittest.TestCase):
    def run_script(self, replies, tool_results=None):
        replies = list(replies)
        executed = []
        tool_results = tool_results or {}

        def chat(messages, tools):
            self.last_messages = messages
            return replies.pop(0)

        def execute(name, arguments):
            executed.append(name)
            result = tool_results.get(name, {})
            if isinstance(result, Exception):
                raise result
            return result

        outcome = email_agent.run_agent("q?", system_prompt="sys", history=[], chat=chat, execute_tool=execute)
        return outcome, executed

    def test_freeform_sql_is_locked_until_products_and_templates_were_checked(self):
        outcome, executed = self.run_script(
            [
                {"tool_calls": [tool_call("run_query", {"cluster_id": 1, "sql": "SELECT 1"})]},
                {"tool_calls": [tool_call("search_data_products", {"search": "sales"}, "c2"),
                                tool_call("list_query_templates", {}, "c3")]},
                {"tool_calls": [tool_call("run_query", {"cluster_id": 1, "sql": "SELECT 1"}, "c4")]},
                {"content": "Net sales were $1,234 on Sep 15."},
            ],
            {"search_data_products": {"products": [{"name": "Store sales"}]},
             "run_query": {"status": "Finished", "query_id": 42, "rows": [[1]]}},
        )
        self.assertEqual(executed, ["search_data_products", "list_query_templates", "run_query"])
        self.assertEqual(outcome.path, email_agent.PATH_FREEFORM)
        self.assertEqual(outcome.query_ids, [42])
        self.assertEqual(outcome.products, ["Store sales"])
        self.assertEqual(outcome.answer, "Net sales were $1,234 on Sep 15.")

    def test_template_path_and_tool_errors_are_returned_to_the_model(self):
        outcome, _ = self.run_script(
            [
                {"tool_calls": [tool_call("run_query_template", {"template": "missing"})]},
                {"tool_calls": [tool_call("run_query_template", {"template": "daily_net_sales", "parameters": {"day": "2026-09-15"}}, "c2")]},
                {"content": "Answer."},
            ],
            {"run_query_template": {"status": "Finished", "query_id": 7}},
        )
        self.assertEqual(outcome.path, email_agent.PATH_TEMPLATE)
        self.assertEqual(outcome.templates, ["missing", "daily_net_sales"])

        replies = [
            {"tool_calls": [tool_call("run_query_template", {"template": "nope"})]},
            {"content": "Could not."},
        ]
        outcome, _ = self.run_script(replies, {"run_query_template": ApiError(404, "No enabled query template named nope.")})
        self.assertEqual(outcome.path, email_agent.PATH_NONE)
        tool_message = next(m for m in self.last_messages if m["role"] == "tool")
        self.assertIn("No enabled query template", tool_message["content"])

    def test_step_limit_yields_a_fallback_answer(self):
        replies = [{"tool_calls": [tool_call("list_clusters", {}, f"c{i}")]} for i in range(email_agent.AGENT_MAX_STEPS)]
        outcome, executed = self.run_script(replies)
        self.assertEqual(len(executed), email_agent.AGENT_MAX_STEPS)
        self.assertIn("couldn't finish", outcome.answer)

    def test_render_reply_escapes_and_labels_the_path(self):
        outcome = email_agent.AgentOutcome(answer="<b>$5</b> for Sep 15", path=email_agent.PATH_FREEFORM, query_ids=[3])
        reply = email_agent.render_reply(outcome, "https://hub.example.com")
        self.assertIn("Freeform draft", reply["text"])
        self.assertIn("https://hub.example.com/#history/3", reply["text"])
        self.assertIn("&lt;b&gt;$5&lt;/b&gt;", reply["html"])
        self.assertNotIn("<b>$5", reply["html"])
        self.assertEqual(email_agent.reply_subject("Sales?"), "Re: Sales?")
        self.assertEqual(email_agent.reply_subject("RE: Sales?"), "RE: Sales?")


class QueueAws(FakeAws):
    def __init__(self):
        super().__init__()
        self.queue = []
        self.deleted = []

    def receive_queue_messages(self, *, region, queue_url, max_messages, wait_seconds):
        batch, self.queue = self.queue[:max_messages], self.queue[max_messages:]
        return batch

    def delete_queue_message(self, *, region, queue_url, receipt_handle):
        self.deleted.append(receipt_handle)


class InboundServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.aws = QueueAws()
        self.app = TrinoHubApp(db_path=Path(self.tmp.name) / "t.sqlite3", aws=self.aws, require_setup_token=False)
        self.app.complete_setup(
            {"username": "admin", "password": "correct-horse-password", "allowed_instance_types": ["r7i.2xlarge"]}
        )
        self.admin = self._user("admin")
        self.app.set_email_settings(
            {
                "enabled": True,
                "from_address": "reports@trinohub.example.com",
                "public_url": "https://hub.example.com",
                "inbound_enabled": True,
                "inbound_address": "ask@trinohub.example.com",
                "inbound_queue_url": "https://sqs.us-east-1.amazonaws.com/123456789012/trinohub-inbound",
            },
            self.admin,
        )
        self.app.create_role({"name": "store-managers", "privileges": ["ASK_BY_EMAIL"]}, self.admin)
        self.app.create_user(
            {"username": "dana", "password": "pw-123456789", "roles": ["user", "store-managers"], "email": "Dana@Example.com"},
            self.admin,
        )
        self.app.create_user(
            {"username": "eli", "password": "pw-123456789", "roles": ["user"], "email": "eli@example.com"}, self.admin
        )
        self.llm_calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def _user(self, username):
        with self.app.conn() as conn:
            return dict(conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone())

    def script_llm(self, replies):
        replies = list(replies)

        def call(messages, tools):
            self.llm_calls.append(messages)
            return replies.pop(0)

        self.app.call_agent_llm = call

    def template_answer(self, template="daily_net_sales", query_id=11, answer="Net sales were $1,234 on Sep 15."):
        ran = []

        def run_query_template(payload, user):
            ran.append((payload["template"], user["username"]))
            return {"status": "Finished", "query_id": query_id, "rows": [[1234]], "columns": ["net_sales"]}

        self.app.run_query_template = run_query_template
        self.script_llm(
            [
                {"tool_calls": [tool_call("search_data_products", {"search": "sales"}),
                                tool_call("list_query_templates", {}, "c2")]},
                {"tool_calls": [tool_call("run_query_template", {"template": template, "parameters": {"day": "2026-09-15"}}, "c3")]},
                {"content": answer},
            ]
        )
        return ran

    def conversations(self):
        return self.app.list_email_conversations()["conversations"]

    def test_answers_verified_sender_with_template_and_threads_the_reply(self):
        ran = self.template_answer()
        result = self.app.handle_inbound_email(ses_notification(raw_email()))
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["path"], "template")
        # The tool ran as the sender, not as an admin or service identity.
        self.assertEqual(ran, [("daily_net_sales", "dana")])
        [reply] = self.aws.sent_emails
        self.assertEqual(reply["to_addresses"], ["dana@example.com"])
        self.assertEqual(reply["subject"], "Re: Sales yesterday?")
        self.assertEqual(reply["headers"]["In-Reply-To"], "<q1@mail.example.com>")
        self.assertIn("<q1@mail.example.com>", reply["headers"]["References"])
        self.assertEqual(reply["headers"]["Auto-Submitted"], "auto-replied")
        self.assertIn("vetted query template daily_net_sales", reply["text_body"])
        self.assertIn("https://hub.example.com/#history/11", reply["text_body"])
        # The question the model saw had the quoted history stripped.
        self.assertEqual(self.llm_calls[0][1], {"role": "user", "content": "What were net sales yesterday?"})
        [row] = self.conversations()
        self.assertEqual((row["username"], row["status"], row["answer_path"], row["query_ids"]), ("dana", "answered", "template", [11]))
        audit = self.app.security_audit_entries()["entries"]
        self.assertTrue(any(entry["action"] == "email.ask" for entry in audit))

        # SQS redelivery of the same message does nothing.
        self.assertEqual(self.app.handle_inbound_email(ses_notification(raw_email()))["status"], "duplicate")
        self.assertEqual(len(self.aws.sent_emails), 1)

    def test_follow_up_carries_thread_history(self):
        self.template_answer()
        self.app.handle_inbound_email(ses_notification(raw_email()))
        self.template_answer(answer="The day before was $999.")
        follow_up = raw_email(
            subject="Re: Sales yesterday?",
            body="And the day before?",
            message_id="<q2@mail.example.com>",
            extra_headers="In-Reply-To: <reply@amazonses.com>\r\nReferences: <q1@mail.example.com> <reply@amazonses.com>\r\n",
        )
        self.llm_calls.clear()
        self.assertEqual(self.app.handle_inbound_email(ses_notification(follow_up, ses_id="ses-2"))["status"], "answered")
        first_turn = self.llm_calls[0]
        self.assertEqual(first_turn[1], {"role": "user", "content": "What were net sales yesterday?"})
        self.assertEqual(first_turn[2], {"role": "assistant", "content": "Net sales were $1,234 on Sep 15."})
        self.assertEqual(first_turn[3], {"role": "user", "content": "And the day before?"})

    def test_spoofed_sender_is_rejected_silently(self):
        self.script_llm([])
        result = self.app.handle_inbound_email(ses_notification(raw_email(), verdicts={"dmarc": "FAIL"}))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.aws.sent_emails, [])
        self.assertEqual(self.llm_calls, [])
        self.assertEqual(self.conversations()[0]["status"], "rejected")

    def test_unknown_or_unprivileged_senders_get_a_refusal_and_no_agent(self):
        self.script_llm([])
        unknown = raw_email(sender="stranger@example.com")
        self.assertEqual(self.app.handle_inbound_email(ses_notification(unknown))["status"], "refused")
        no_privilege = raw_email(sender="eli@example.com")
        self.assertEqual(self.app.handle_inbound_email(ses_notification(no_privilege, ses_id="ses-2"))["status"], "refused")
        self.assertEqual([mail["to_addresses"] for mail in self.aws.sent_emails], [["stranger@example.com"], ["eli@example.com"]])
        self.assertIn("isn't set up", self.aws.sent_emails[0]["text_body"])
        self.assertEqual(self.llm_calls, [])

    def test_automated_and_self_sent_mail_is_ignored(self):
        self.script_llm([])
        auto = raw_email(extra_headers="Auto-Submitted: auto-replied\r\n")
        self.assertEqual(self.app.handle_inbound_email(ses_notification(auto))["status"], "ignored")
        own = raw_email(sender="reports@trinohub.example.com")
        self.assertEqual(self.app.handle_inbound_email(ses_notification(own, ses_id="ses-2"))["status"], "ignored")
        self.assertEqual(self.aws.sent_emails, [])

    def test_hourly_limit(self):
        from trinohub import server as server_module

        original = server_module.EMAIL_QUESTIONS_PER_HOUR
        server_module.EMAIL_QUESTIONS_PER_HOUR = 1
        try:
            self.template_answer()
            self.app.handle_inbound_email(ses_notification(raw_email()))
            self.script_llm([])
            second = raw_email(message_id="<q2@x>")
            self.assertEqual(self.app.handle_inbound_email(ses_notification(second, ses_id="ses-2"))["status"], "limited")
            self.assertIn("limit", self.aws.sent_emails[-1]["text_body"])
        finally:
            server_module.EMAIL_QUESTIONS_PER_HOUR = original

    def test_llm_failure_sends_an_apology_and_records_failure(self):
        def broken(messages, tools):
            raise ApiError(502, "The AI provider is having trouble right now.")

        self.app.call_agent_llm = broken
        result = self.app.handle_inbound_email(ses_notification(raw_email()))
        self.assertEqual(result["status"], "failed")
        self.assertIn("couldn't answer", self.aws.sent_emails[0]["text_body"])
        self.assertEqual(self.conversations()[0]["status"], "failed")

    def test_email_agent_freeform_sql_is_select_only(self):
        with self.assertRaises(ApiError):
            self.app.email_agent_tool("run_query", {"cluster_id": 1, "sql": "SHOW TABLES"}, self._user("dana"))
        with self.assertRaises(ApiError):
            self.app.email_agent_tool("run_query", {"cluster_id": 1, "sql": "DELETE FROM sales"}, self._user("dana"))

    def test_poll_deletes_every_message_even_unparseable_ones(self):
        self.template_answer()
        self.aws.queue = [
            {"receipt_handle": "h1", "body": "garbage"},
            {"receipt_handle": "h2", "body": ses_notification(raw_email())},
        ]
        self.assertEqual(self.app.poll_inbound_email_once(), 2)
        self.assertEqual(self.aws.deleted, ["h1", "h2"])
        self.assertEqual(len(self.aws.sent_emails), 1)

    def test_poll_is_a_no_op_when_inbound_is_disabled(self):
        self.app.set_email_settings({"inbound_enabled": False}, self.admin)
        self.aws.queue = [{"receipt_handle": "h1", "body": "x"}]
        self.assertEqual(self.app.poll_inbound_email_once(), 0)
        self.assertEqual(self.aws.deleted, [])

    def test_inbound_settings_validation(self):
        with self.assertRaises(ApiError):
            self.app.set_email_settings({"inbound_queue_url": "https://example.com/queue"}, self.admin)
        with self.assertRaises(ApiError):
            self.app.set_email_settings({"inbound_address": "not an address"}, self.admin)
        with self.assertRaises(ApiError):
            self.app.set_email_settings({"enabled": False}, self.admin)  # inbound still on


if __name__ == "__main__":
    unittest.main()
