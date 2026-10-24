from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from gov_report.crawler import GovCrawler
from gov_report.llm_classifier import JSON_SCHEMA, LLMClassifier
from gov_report.llm_transport import ModelCallError, api_bases, decode_response, parse_judgment
from gov_report.parser import Article


def judgment(**changes):
    value = dict(include=True, final_category="policy", policy_subtype="通知", document_action="发布新文件",
                is_personnel=False, is_policy=True, relevance_to_pesticide_chemical_enterprise="high",
                related_directions=["化工/危化品"], reason="正式申报通知", summary="化工企业申报。",
                change_points=["公布申报条件"], exclude_reason="", confidence=0.98)
    return {**value, **changes}


def response(payload, status=200, mime="application/json"):
    result = requests.Response()
    result.status_code = status
    result.headers["Content-Type"] = mime
    result.encoding = "utf-8"
    result._content = (payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)).encode("utf-8")
    result._content_consumed = True
    return result


def chat(content=None, **message):
    return response({"choices": [{"message": {"content": json.dumps(judgment(), ensure_ascii=False) if content is None else content,
                                                **message}, "finish_reason": "stop"}]})


class ResponseTests(unittest.TestCase):
    def test_chat_content_string_parts_and_sdk_parsed_object(self):
        text = json.dumps(judgment(), ensure_ascii=False)
        variants = [chat(text), chat([{"type": "text", "text": text}]),
                    chat("", parsed=judgment()), chat("说明如下：\n```json\n" + text + "\n```"),
                    chat("<think>internal {not valid}</think>\n" + text)]
        for value in variants:
            self.assertTrue(decode_response(value, JSON_SCHEMA)["include"])

    def test_responses_output_text_and_message_parts(self):
        text = json.dumps(judgment(), ensure_ascii=False)
        for payload in ({"output_text": text},
                        {"status": "completed", "output": [{"type": "reasoning", "summary": []},
                         {"type": "message", "content": [{"type": "output_text", "text": text}]}]}):
            self.assertTrue(decode_response(response(payload), JSON_SCHEMA)["include"])

    def test_chat_sse_is_decoded_even_when_the_proxy_ignores_stream_false(self):
        text = json.dumps(judgment(), ensure_ascii=False)
        events = []
        for part in (text[:20], text[20:]):
            events.append("data: " + json.dumps({"choices": [{"index": 0, "delta": {"content": part}}]}))
        events += ["data: " + json.dumps({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}), "data: [DONE]"]
        self.assertTrue(decode_response(response("\n\n".join(events), mime="text/event-stream"), JSON_SCHEMA)["include"])

    def test_responses_sse_completion_is_decoded(self):
        payload = {"type": "response.completed", "response": {"status": "completed", "output_text": json.dumps(judgment())}}
        self.assertTrue(decode_response(response("event: response.completed\ndata: " + json.dumps(payload) + "\n\n",
                                               mime="text/event-stream"), JSON_SCHEMA)["include"])

    def test_missing_or_mistyped_fields_cannot_be_silently_treated_as_exclusions(self):
        invalid = [{}, {"error": "permission denied"}, {**judgment(), "include": "false"},
                   {**judgment(), "confidence": float("nan")}, {**judgment(), "change_points": "not a list"},
                   {**judgment(), "document_action": "not a known action"}]
        for value in invalid:
            with self.assertRaises(ModelCallError):
                parse_judgment(value, JSON_SCHEMA)

    def test_html_and_empty_responses_have_specific_safe_diagnostics(self):
        secret = "local-private-value"
        for value, expected in ((response("<html>" + secret + "</html>", mime="text/html"), "HTML"),
                                (response(""), "为空"), (response("not json " + secret), "不是 JSON")):
            with self.assertRaises(ModelCallError) as caught:
                decode_response(value, JSON_SCHEMA)
            self.assertIn(expected, str(caught.exception))
            self.assertIn("HTTP 200", str(caught.exception))
            self.assertNotIn(secret, str(caught.exception))

    def test_refusals_incomplete_and_reasoning_only_are_not_accepted(self):
        cases = [chat("", refusal="cannot comply"), response({"status": "incomplete", "output_text": json.dumps(judgment())}),
                 response({"choices": [{"message": {"content": json.dumps(judgment())}, "finish_reason": "length"}]}),
                 response({"output": [{"type": "reasoning", "summary": [{"text": json.dumps(judgment())}]}]})]
        for value in cases:
            with self.assertRaises(ModelCallError):
                decode_response(value, JSON_SCHEMA)

    def test_truncated_or_error_sse_is_not_accepted(self):
        text = json.dumps(judgment())
        payload = "data: " + json.dumps({"choices": [{"delta": {"content": text}}]})
        for raw in (payload, payload + '\n\ndata: {"error":{"message":"fixture"}}\n\n'):
            with self.assertRaises(ModelCallError):
                decode_response(response(raw, mime="text/event-stream"), JSON_SCHEMA)

    def test_only_same_origin_v1_is_suggested_and_custom_prefixes_are_preserved(self):
        self.assertEqual(api_bases("https://example.com"), ["https://example.com", "https://example.com/v1"])
        self.assertEqual(api_bases("https://example.com/custom/models"), ["https://example.com/custom"])
        self.assertEqual(api_bases("https://example.com/v1/responses"), ["https://example.com/v1"])
        for value in ("not a url", "https://example.com?key=private", "https://" + "user:password@" + "example.com"):
            with self.assertRaises(ModelCallError):
                api_bases(value)


class NegotiationTests(unittest.TestCase):
    def setUp(self):
        self.settings = patch.multiple("gov_report.llm_classifier", OPENAI_API_KEY="fixture-key",
                                       OPENAI_MODEL="fixture-model", OPENAI_BASE_URL="https://example.com",
                                       OPENAI_API_STYLE="auto", OPENAI_MAX_RETRIES=2)
        self.settings.start()
        self.sleep = patch("gov_report.llm_classifier.time.sleep").start()
        self.post = patch("gov_report.llm_transport.requests.post").start()
        self.classifier = LLMClassifier(cache_enabled=False)

    def tearDown(self):
        patch.stopall()

    def test_html_site_root_falls_back_to_v1_and_remembers_successful_route(self):
        self.post.side_effect = [response("<html>home</html>", mime="text/html"),
                                 response("<html>home</html>", mime="text/html"), chat(), chat()]
        first = self.classifier.classify_article({"title": "test"})
        second = self.classifier.classify_article({"title": "another"})
        self.assertTrue(first["call_succeeded"])
        self.assertTrue(second["call_succeeded"])
        self.assertEqual(first["api_prefix"], "/v1")
        self.assertEqual(self.post.call_count, 4)
        self.assertEqual([call.args[0] for call in self.post.call_args_list][-2:],
                         ["https://example.com/v1/chat/completions"] * 2)
        self.assertTrue(all(call.kwargs["allow_redirects"] is False for call in self.post.call_args_list))

    def test_http_200_bad_json_or_empty_content_really_downgrades_format(self):
        for failed in (response("not json"), chat(""), chat("{}")):
            self.post.reset_mock()
            self.post.side_effect = [failed, chat("") , chat()]
            result = LLMClassifier(cache_enabled=False).classify_article({})
            self.assertTrue(result["call_succeeded"])
            self.assertEqual(result["response_mode"], "plain")
            bodies = [call.kwargs["json"] for call in self.post.call_args_list]
            self.assertEqual(bodies[0]["response_format"]["type"], "json_schema")
            self.assertEqual(bodies[1]["response_format"]["type"], "json_object")
            self.assertNotIn("response_format", bodies[2])
            self.assertFalse(bodies[2]["stream"])

    def test_unsupported_schema_downgrades_to_json_object(self):
        self.post.side_effect = [response({"error": {"message": "response_format unsupported"}}, 400), chat()]
        result = self.classifier.classify_article({})
        self.assertTrue(result["call_succeeded"])
        self.assertEqual(result["response_mode"], "json_object")

    def test_unsupported_temperature_is_removed_without_changing_model(self):
        self.post.side_effect = [response({"error": {"message": "temperature not supported"}}, 400), chat(), chat()]
        self.assertTrue(self.classifier.classify_article({})["call_succeeded"])
        self.assertTrue(self.classifier.classify_article({"title": "second"})["call_succeeded"])
        self.assertIn("temperature", self.post.call_args_list[0].kwargs["json"])
        self.assertNotIn("temperature", self.post.call_args_list[1].kwargs["json"])
        self.assertNotIn("temperature", self.post.call_args_list[2].kwargs["json"])
        self.assertTrue(all(call.kwargs["json"]["model"] == "fixture-model" for call in self.post.call_args_list))

    def test_responses_only_service_can_be_used_automatically(self):
        self.post.side_effect = [response({}, 404), response({"output_text": json.dumps(judgment())})]
        result = self.classifier.classify_article({})
        self.assertTrue(result["call_succeeded"])
        self.assertEqual(result["api_style"], "responses")
        self.assertIn("text", self.post.call_args.kwargs["json"])
        self.assertNotIn("response_format", self.post.call_args.kwargs["json"])

    def test_explicit_api_style_is_respected(self):
        self.post.return_value = response({"output_text": json.dumps(judgment())})
        with patch("gov_report.llm_classifier.OPENAI_API_STYLE", "responses"):
            self.assertTrue(self.classifier.classify_article({})["call_succeeded"])
        self.assertTrue(self.post.call_args.args[0].endswith("/responses"))

    def test_authentication_balance_and_permissions_fail_once_without_exposing_server_text(self):
        for status in (401, 402, 403):
            self.post.reset_mock()
            self.post.return_value = response({"error": {"message": "fixture-key private data"}}, status)
            result = self.classifier.classify_article({})
            self.assertFalse(result["call_succeeded"])
            self.assertIn(str(status), result["reason"])
            self.assertNotIn("fixture-key", result["reason"])
            self.assertEqual(self.post.call_count, 1)

    def test_transient_failure_is_retried_but_does_not_trigger_format_cycling(self):
        self.post.side_effect = [response({}, 429), chat()]
        self.assertTrue(self.classifier.classify_article({})["call_succeeded"])
        self.assertEqual(self.post.call_count, 2)
        self.assertEqual([call.kwargs["json"]["response_format"]["type"] for call in self.post.call_args_list],
                         ["json_schema", "json_schema"])

    def test_network_errors_are_sanitized(self):
        self.post.side_effect = requests.ConnectionError("fixture-key https://private.example.com/")
        result = self.classifier.classify_article({})
        self.assertFalse(result["call_succeeded"])
        self.assertIn("ConnectionError", result["reason"])
        self.assertNotIn("fixture-key", result["reason"])
        self.assertNotIn("private.example", result["reason"])

    def test_cache_saves_successes_not_transport_failures(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.jsonl"
            classifier = LLMClassifier(path)
            self.post.return_value = response({}, 401)
            self.assertFalse(classifier.classify_article({})["call_succeeded"])
            self.assertFalse(path.exists())
            self.post.return_value = chat()
            self.assertTrue(classifier.classify_article({})["call_succeeded"])
            self.assertTrue(classifier.classify_article({})["from_cache"])
            self.assertEqual(self.post.call_count, 2)

    def test_failure_is_not_labeled_as_a_model_semantic_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            crawler = GovCrawler([], {}, folder, use_cache=False)
            crawler.rule_bucket = Mock(return_value=("ambiguous", "fixture"))
            crawler.llm = Mock()
            crawler.llm.classify_article.return_value = self.classifier._fallback_result("LLM调用失败：HTTP 200；返回 HTML")
            article = Article("化工申报通知", "https://example.gov.cn/a", None, "正文", [])
            decision = crawler.decide_with_optional_llm({"name": "fixture"}, article, None, {})
            self.assertEqual(decision["status"], "llm_failed")
            self.assertNotIn("复判排除", decision["reason"])
            self.assertEqual(crawler.llm_statistics()["failure_count"], 1)
            self.assertEqual(crawler.llm_statistics()["success_count"], 0)


if __name__ == "__main__":
    unittest.main()
