import re
import tempfile
import unittest
from pathlib import Path

from tools.repo_guard.terms import BUILTIN_TERM_DIGESTS, TermMatcher, iter_words, load_local_terms, phrase_digest


class WordSplittingTests(unittest.TestCase):
    def test_camel_case_and_separators(self):
        words = [word for word, _, _ in iter_words("HTTPServer parseOrderId snake_case2value")]
        self.assertEqual(words, ["http", "server", "parse", "order", "id", "snake", "case", "value"])

    def test_spans_point_into_the_original_text(self):
        text = "call fooBar now"
        spans = {word: text[start:end] for word, start, end in iter_words(text)}
        self.assertEqual(spans["bar"], "Bar")


class BuiltinPhraseTests(unittest.TestCase):
    def setUp(self):
        self.matcher = TermMatcher(digests={phrase_digest("forbidden"), phrase_digest("blocked phrase here")})

    def test_single_word_in_any_case_or_identifier(self):
        for text in ("a Forbidden word", "useForbiddenApi()", "forbidden_value = 1", "x.forbidden.com"):
            with self.subTest(text=text):
                self.assertIsNotNone(self.matcher.search(text))

    def test_multi_word_phrase(self):
        text = "this is a Blocked-Phrase_Here example"
        start, end = self.matcher.search(text)
        self.assertEqual(text[start:end], "Blocked-Phrase_Here")

    def test_words_inside_hashes_are_ignored(self):
        text = '"integrity": "sha512-Vj1jF3cPfxg7OAfoForbidden2JF9pnVHrX8qx7AHMiYWT+NDAA7jChlNgRS4WTLc=="'
        self.assertIsNone(self.matcher.search(text))

    def test_partial_words_do_not_match(self):
        self.assertIsNone(self.matcher.search("forbiddance and blocked phrases"))

    def test_builtin_digests_are_well_formed(self):
        self.assertTrue(BUILTIN_TERM_DIGESTS)
        for digest in BUILTIN_TERM_DIGESTS:
            self.assertRegex(digest, re.compile(r"^[0-9a-f]{64}$"))


class LocalLiteralTests(unittest.TestCase):
    def test_numbers_match_any_formatting_and_prefix(self):
        matcher = TermMatcher(digests=(), literals=["0935 184 7264"])  # repo-guard: allow
        for text in ("09351847264", "+98 935-184-7264", "۰۹۳۵۱۸۴۷۲۶۴", "00989351847264"):  # repo-guard: allow
            with self.subTest(text=text):
                self.assertIsNotNone(matcher.search(text))
        self.assertIsNone(matcher.search("109351847264"))  # repo-guard: allow

    def test_text_matches_case_and_whitespace_insensitively(self):
        matcher = TermMatcher(digests=(), literals=["Sample  Parts Shop", "خیابان نمونه"])
        self.assertIsNotNone(matcher.search("welcome to sample parts\tshop"))
        self.assertIsNotNone(matcher.search("آدرس: خيابان نمونه"))

    def test_short_literals_are_ignored(self):
        self.assertEqual(TermMatcher(digests=(), literals=["ab", "12"]).literal_count, 0)

    def test_local_file_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "terms"
            path.write_text("﻿# comment\n\nfirst term\n  second term  \n", encoding="utf-8")
            self.assertEqual(load_local_terms(path), ["first term", "second term"])
            self.assertEqual(load_local_terms(Path(directory) / "missing"), [])


if __name__ == "__main__":
    unittest.main()
