import unittest

from tools.repo_guard.gitio import _unquote, parse_added_lines

PATCH = """\
diff --git a/shop/views.py b/shop/views.py
index 1111111..2222222 100644
--- a/shop/views.py
+++ b/shop/views.py
@@ -10,0 +11,2 @@ def index(request):
+first added
++++ looks like a header
@@ -20 +22 @@ def detail(request):
-old line
+replacement
diff --git a/old.txt b/old.txt
deleted file mode 100644
--- a/old.txt
+++ /dev/null
@@ -1 +0,0 @@
-gone
diff --git a/docs/my notes.md b/docs/my notes.md
new file mode 100644
--- /dev/null
+++ b/docs/my notes.md\t
@@ -0,0 +1 @@
+note
\\ No newline at end of file
"""


class PatchParsingTests(unittest.TestCase):
    def test_added_lines_and_numbers(self):
        lines = [(line.path, line.number, line.text) for line in parse_added_lines(PATCH)]
        self.assertEqual(
            lines,
            [
                ("shop/views.py", 11, "first added"),
                ("shop/views.py", 12, "+++ looks like a header"),
                ("shop/views.py", 22, "replacement"),
                ("docs/my notes.md", 1, "note"),
            ],
        )

    def test_unquote(self):
        self.assertEqual(_unquote('"b/dir/a\\"b\\\\c.txt"'), 'b/dir/a"b\\c.txt')
        self.assertEqual(_unquote('"b/\\321\\201.txt"'), "b/с.txt")
        self.assertEqual(_unquote("b/plain.txt"), "b/plain.txt")


if __name__ == "__main__":
    unittest.main()
