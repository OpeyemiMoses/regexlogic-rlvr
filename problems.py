"""
RegexLogic Problem Bank
A curated benchmark suite of formal regular expression problems spanning:
- ReDoS Refactoring & Catastrophic Backtracking Immunity
- Deterministic Finite Automata (DFA) & State Constraints
- Lookaround & Negative Assertion Logic
- Strict Structured Data Tokens (SemVer, IPv4/6, ISO-8601, Cron)
- Delimiter, Quoting, and Escape Sequence Handling

Each problem includes:
- Clear mathematical / semantic specification
- Positive test cases (must match)
- Negative test cases (must reject)
- Pathological evil payloads (tests ReDoS resilience)
"""

from typing import List, Dict, Any

PROBLEMS: List[Dict[str, Any]] = [
    # -------------------------------------------------------------
    # Category 1: ReDoS Refactoring & Catastrophic Backtracking Defense
    # -------------------------------------------------------------
    {
        "id": "redos_01_nested_word_repeats",
        "category": "redos_defense",
        "title": "Nested Word Repetition Refactor",
        "prompt": (
            "Write a Python regular expression that matches a sequence of words separated by spaces "
            "ending with an exclamation mark, like 'hello world!'. "
            "CRITICAL: Avoid catastrophic backtracking (ReDoS). A naive pattern like r'^((\\w+)\\s*)+!$' "
            "hangs on strings like 'a a a a a ... a'. Your regex must process pathological input in linear time. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "hello!",
            "hello world!",
            "the quick brown fox jumps over the lazy dog!",
            "word1 word2 word3!"
        ],
        "negative": [
            "hello",
            "hello world",
            "hello world? ",
            "!hello",
            "hello ! world"
        ],
        "redos_payloads": [
            "word " * 28 + "x",
            "a " * 35 + "!",
            "test " * 30 + "wrong"
        ],
        "canonical_ref": r"^\w+(?:\s+\w+)*!$"
    },
    {
        "id": "redos_02_safe_email_localpart",
        "category": "redos_defense",
        "title": "ReDoS-Safe Email Local-Part Parser",
        "prompt": (
            "Write a regular expression that validates an email local-part (before the '@'). "
            "It must consist of alphanumeric characters and dots, but CANNOT start or end with a dot, "
            "and CANNOT have two consecutive dots (e.g. 'john.doe' is valid, 'john..doe' is invalid). "
            "Ensure the pattern is completely immune to catastrophic backtracking when given long strings "
            "of characters followed by an invalid character. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "john",
            "john.doe",
            "alice.smith.dev",
            "user123.test456"
        ],
        "negative": [
            ".john",
            "john.",
            "john..doe",
            "john@doe",
            "john.doe..test"
        ],
        "redos_payloads": [
            "a." * 25 + "a." * 25 + "!",
            "user" * 30 + "..wrong",
            "a" * 50 + "."
        ],
        "canonical_ref": r"^[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*$"
    },
    {
        "id": "redos_03_safe_comma_separated_quoted",
        "category": "redos_defense",
        "title": "Safe Comma-Separated Values with Optional Quotes",
        "prompt": (
            "Write a regex matching comma-separated list of items where each item is either plain alphanumeric "
            "OR enclosed in double quotes (e.g. 'apple,\"banana\",cherry'). Items cannot be empty. "
            "Must be strictly linear time and resist ReDoS when matching long lists. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "apple",
            '"banana"',
            'apple,"banana",cherry',
            '"alpha","beta","gamma"',
            '1,2,"3",4'
        ],
        "negative": [
            "",
            ",",
            "apple,",
            ',apple',
            'apple,"unclosed',
            'apple,"banana"orange'
        ],
        "redos_payloads": [
            '"item",' * 28 + "bad",
            "val," * 32 + '"unclosed'
        ],
        "canonical_ref": r'^(?:[a-zA-Z0-9]+|"[^"\n]*")(?:,(?:[a-zA-Z0-9]+|"[^"\n]*"))*$'
    },
    {
        "id": "redos_04_safe_url_slug_hierarchy",
        "category": "redos_defense",
        "title": "Safe URL Path Hierarchy",
        "prompt": (
            "Write a regex matching valid URL slugs separated by slashes without trailing slash, "
            "such as '/blog/2026/my-post'. Each segment must start with a slash and contain lowercase letters, "
            "numbers, or hyphens (cannot start or end with a hyphen). Must not catastrophically backtrack. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "/home",
            "/blog/my-post",
            "/docs/v2/api-reference-123",
            "/a/b/c"
        ],
        "negative": [
            "home",
            "/",
            "/blog/",
            "/blog/-invalid",
            "/blog/invalid-",
            "/blog//double"
        ],
        "redos_payloads": [
            "/slug" * 30 + "/",
            "/a-b" * 30 + "-!"
        ],
        "canonical_ref": r"^(?:/[a-z0-9]+(?:-[a-z0-9]+)*)+$"
    },

    # -------------------------------------------------------------
    # Category 2: Automata & Formal Language Constraints
    # -------------------------------------------------------------
    {
        "id": "automata_01_binary_divisible_by_3",
        "category": "automata_theory",
        "title": "Binary Numbers Divisible by 3 (DFA)",
        "prompt": (
            "Write a regular expression that matches any non-empty binary string (consisting only of '0' and '1') "
            "that represents a binary number divisible by 3. Leading zeros are permitted. "
            "For example: '0' (0), '11' (3), '110' (6), '1001' (9), '1100' (12) are valid. "
            "'1' (1), '10' (2), '100' (4), '101' (5), '111' (7) are invalid. "
            "Construct the regex from the minimal 3-state DFA. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "0",
            "000",
            "11",
            "110",
            "1001",
            "1100",
            "1111",
            "10010"
        ],
        "negative": [
            "",
            "1",
            "10",
            "100",
            "101",
            "111",
            "1000",
            "1010",
            "1011"
        ],
        "redos_payloads": [
            "01" * 30 + "00",
            "1" * 60
        ],
        "canonical_ref": r"^(?:0|1(?:01*0)*1)+$"
    },
    {
        "id": "automata_02_even_zeros_odd_ones",
        "category": "automata_theory",
        "title": "Even Number of 0s and Odd Number of 1s",
        "prompt": (
            "Write a regular expression matching any non-empty binary string containing an EVEN number of '0's "
            "and an ODD number of '1's. "
            "For instance: '1' (0 zeros, 1 one -> valid), '001' (2 zeros, 1 one -> valid), '010' (valid), "
            "'111' (0 zeros, 3 ones -> valid). '01' (1 zero -> invalid), '0011' (2 ones -> invalid). "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "1",
            "001",
            "010",
            "100",
            "111",
            "01011",
            "10000"
        ],
        "negative": [
            "",
            "0",
            "01",
            "10",
            "11",
            "00",
            "0011",
            "0001"
        ],
        "redos_payloads": [
            "00" * 25 + "11" * 25,
            "10" * 30
        ],
        "canonical_ref": r"^(?:(?:00|11)|(?:01|10)(?:00|11)*(?:01|10))*(?:1|(?:01|10)(?:00|11)*0)$"
    },
    {
        "id": "automata_03_no_consecutive_identical_chars",
        "category": "automata_theory",
        "title": "Strict Alternating Alphabet String",
        "prompt": (
            "Write a regex over the alphabet {a, b, c} of length at least 1 such that no two adjacent characters "
            "are identical (e.g. 'abacb' is valid, 'abbc' is invalid). "
            "Use negative lookahead to strictly forbid identical adjacent characters. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "a",
            "ab",
            "aba",
            "abc",
            "abacbca",
            "cbabc"
        ],
        "negative": [
            "",
            "aa",
            "abb",
            "aab",
            "abacc",
            "d",
            "ab d"
        ],
        "redos_payloads": [
            "ab" * 35 + "c",
            "abc" * 25 + "a"
        ],
        "canonical_ref": r"^(?:([abc])(?!\1))+$"
    },

    # -------------------------------------------------------------
    # Category 3: Lookaround & Constraint Logic
    # -------------------------------------------------------------
    {
        "id": "lookaround_01_strong_password_rules",
        "category": "lookaround_logic",
        "title": "Multi-Constraint Password Validation",
        "prompt": (
            "Write a regular expression that validates a strong password with all the following criteria: "
            "1. Length between 10 and 32 characters. "
            "2. At least one uppercase letter [A-Z]. "
            "3. At least one lowercase letter [a-z]. "
            "4. At least one digit [0-9]. "
            "5. At least one special character from [!@#$%^&*]. "
            "6. Must NOT contain the substring 'password' or 'admin' (case-insensitive). "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "CorrectHorse#1",
            "P@ssw0rdValid!",
            "SuperSecret99$",
            "V3ryStr0ng!Key"
        ],
        "negative": [
            "Short1!",
            "nouppercase123!",
            "NOLOWERCASE123!",
            "NoDigitsHere!",
            "NoSpecialChar123",
            "myPassword!123",
            "adminAccess#2026"
        ],
        "redos_payloads": [
            "Aa1!" + "x" * 28,
            "VeryLongSecretKey123!@#" * 5
        ],
        "canonical_ref": r"^(?!.*(?i:password|admin))(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z0-9!@#$%^&*]{10,32}$"
    },
    {
        "id": "lookaround_02_negative_extension_filter",
        "category": "lookaround_logic",
        "title": "Filename Filter with Forbidden Extensions",
        "prompt": (
            "Write a regex matching filenames with an alphanumeric name, a dot, and an extension, "
            "EXCEPT files with extensions .exe, .bat, or .sh (case-insensitive). "
            "Valid examples: 'photo.jpg', 'data.csv', 'archive.tar.gz'. "
            "Invalid: 'run.exe', 'script.SH', 'bad.bat'. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "document.pdf",
            "image.png",
            "backup.tar.gz",
            "source.py",
            "notes.txt"
        ],
        "negative": [
            "installer.exe",
            "INSTALLER.EXE",
            "setup.bat",
            "deploy.sh",
            "test.Sh",
            "noextension"
        ],
        "redos_payloads": [
            "file" * 30 + ".pdf",
            "a" * 40 + ".exe"
        ],
        "canonical_ref": r"^(?!.*(?i:\.(?:exe|bat|sh))$)[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+$"
    },
    {
        "id": "lookaround_03_surrounded_tag_content",
        "category": "lookaround_logic",
        "title": "Balanced Tag Content Extractor",
        "prompt": (
            "Write a regular expression that matches the content between matching brackets [bracket] or (paren) "
            "or {brace}, asserting that opening and closing delimiters match symmetrically. "
            "For example '[test]' or '(sample)' or '{code}'. Mismatched pairs like '[sample)' or '(code}' must fail. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "[test]",
            "(sample)",
            "{code}",
            "[12345]",
            "(hello world)"
        ],
        "negative": [
            "[sample)",
            "(test]",
            "{mismatch]",
            "[unclosed",
            "unopened]",
            "[]"
        ],
        "redos_payloads": [
            "[" + "a" * 50 + "]",
            "(" + "x" * 50 + ")"
        ],
        "canonical_ref": r"^(?:\[(?=[^\]]+\])([^\]]+)\]|\((?=[^\)]+\))([^\)]+)\)|\{(?=[^\}]+\})([^\}]+)\})$"
    },

    # -------------------------------------------------------------
    # Category 4: Strict Structured Data Parsers
    # -------------------------------------------------------------
    {
        "id": "struct_01_strict_ipv4_octet_range",
        "category": "structured_data",
        "title": "Strict IPv4 Address with 0-255 Octet Verification",
        "prompt": (
            "Write a regular expression that matches a valid IPv4 address in dot-decimal notation. "
            "Each of the 4 octets must be strictly between 0 and 255. Leading zeros in multi-digit numbers "
            "are FORBIDDEN (e.g. '192.168.01.1' is invalid, '0.0.0.0' is valid). "
            "Numbers > 255 (like 256 or 300) must be rejected. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "0.0.0.0",
            "127.0.0.1",
            "192.168.1.1",
            "255.255.255.255",
            "10.0.254.99"
        ],
        "negative": [
            "256.1.1.1",
            "192.168.01.1",
            "192.168.1.00",
            "1.2.3.4.5",
            "1.2.3",
            "1.2.3.999",
            "300.0.0.0"
        ],
        "redos_payloads": [
            "192.168.1." * 15 + "255",
            "255." * 25 + "!"
        ],
        "canonical_ref": r"^(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)$"
    },
    {
        "id": "struct_02_semantic_versioning_2_0",
        "category": "structured_data",
        "title": "Strict SemVer 2.0.0 Specification",
        "prompt": (
            "Write a regex matching full Semantic Versioning 2.0.0 format. "
            "MAJOR.MINOR.PATCH with optional pre-release (-alpha.1) and optional build metadata (+20260101). "
            "Leading zeros in numeric identifiers are forbidden (e.g. '01.0.0' is invalid, '0.1.0' is valid). "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "0.0.4",
            "1.2.3",
            "10.20.30",
            "1.1.2-prerelease+meta",
            "1.0.0-alpha.1",
            "1.0.0-0.3.7",
            "1.0.0+20130313144700"
        ],
        "negative": [
            "1",
            "1.2",
            "01.1.1",
            "1.02.1",
            "1.1.03",
            "1.2.3-",
            "1.2.3+",
            "v1.2.3"
        ],
        "redos_payloads": [
            "1.0.0-" + "alpha." * 25 + "!",
            "10.20.30+" + "build." * 25 + "!"
        ],
        "canonical_ref": r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    },
    {
        "id": "struct_03_iso_8601_strict_timestamp",
        "category": "structured_data",
        "title": "ISO-8601 UTC / Offset Timestamp",
        "prompt": (
            "Write a regular expression matching an ISO-8601 date-time string in format "
            "YYYY-MM-DDTHH:MM:SS with optional fraction of a second (.sss) and either 'Z' or a valid "
            "timezone offset [+-]HH:MM. "
            "Hours must be 00-23, minutes and seconds 00-59. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "2026-10-23T12:00:00Z",
            "2026-01-01T00:00:00.123Z",
            "2026-07-15T23:59:59+01:00",
            "2026-12-31T18:30:00.999-05:00"
        ],
        "negative": [
            "2026-10-23",
            "2026-10-23 12:00:00",
            "2026-10-23T24:00:00Z",
            "2026-10-23T12:60:00Z",
            "2026-10-23T12:00:60Z",
            "2026-10-23T12:00:00+25:00"
        ],
        "redos_payloads": [
            "2026-10-23T12:00:00." + "9" * 40 + "Z"
        ],
        "canonical_ref": r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
    },
    {
        "id": "struct_04_standard_cron_expression",
        "category": "structured_data",
        "title": "Standard 5-Field Cron Expression",
        "prompt": (
            "Write a regex matching a standard 5-field cron expression (minute hour dom month dow). "
            "Fields are separated by single spaces. "
            "Allow single numbers, asterisks '*', step values '*/5', and comma-separated lists '1,2,3'. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "* * * * *",
            "*/5 * * * *",
            "0 12 * * 1-5",
            "30 4 1,15 * 5",
            "0 0 1 1 *"
        ],
        "negative": [
            "* * * *",
            "* * * * * *",
            "*/ * * * *",
            "60 * * * *",
            "empty"
        ],
        "redos_payloads": [
            "*/1," * 20 + "5 * * * *"
        ],
        "canonical_ref": r"^(?:(?:\*|(?:[0-5]?\d)(?:-[0-5]?\d)?)(?:/[0-5]?\d)?(?:,(?:(?:\*|(?:[0-5]?\d)(?:-[0-5]?\d)?)(?:/[0-5]?\d)?))*)\s+(?:(?:\*|(?:1\d|2[0-3]|\d)(?:-(?:1\d|2[0-3]|\d))?)(?:/(?:1\d|2[0-3]|\d))?)\s+(?:(?:\*|(?:[12]\d|3[01]|[1-9])(?:-(?:[12]\d|3[01]|[1-9]))?)(?:,(?:[12]\d|3[01]|[1-9]))*)\s+(?:(?:\*|(?:1[0-2]|[1-9])))\s+(?:(?:\*|[0-7](?:-[0-7])?))$"
    },

    # -------------------------------------------------------------
    # Category 5: Delimiters, Escaping & Code Syntax
    # -------------------------------------------------------------
    {
        "id": "delim_01_json_escaped_string",
        "category": "syntax_parsing",
        "title": "JSON-Compliant String with Escape Sequences",
        "prompt": (
            "Write a regex that matches a valid JSON double-quoted string literal. "
            "It must start and end with double quotes. Inside, it can contain any character except unescaped "
            "quotes or control characters. Allowed escape sequences are \\\", \\\\, \\/, \\b, \\f, \\n, \\r, \\t, "
            "or unicode escapes \\uXXXX where X is a hex digit. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            '""',
            '"hello world"',
            r'"line 1\nline 2"',
            r'"escaped \"quote\" inside"',
            r'"unicode \u0041\u0042"',
            r'"path\\to\\file"'
        ],
        "negative": [
            '',
            '"unclosed string',
            'unescaped " quote"',
            r'"invalid \escape"',
            r'"bad unicode \u12G4"'
        ],
        "redos_payloads": [
            '"' + r"\\" * 30 + '"',
            '"' + "a" * 50 + '"'
        ],
        "canonical_ref": r'^"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"$'
    },
    {
        "id": "delim_02_markdown_inline_links",
        "category": "syntax_parsing",
        "title": "Markdown Inline Link [text](url) Parser",
        "prompt": (
            "Write a regex matching a complete markdown inline link [anchor text](https://url). "
            "The anchor text inside brackets cannot be empty and cannot contain square brackets. "
            "The URL inside parentheses must start with http:// or https:// and cannot contain spaces or parens. "
            "Output only the final regex pattern in backticks."
        ),
        "positive": [
            "[Google](https://google.com)",
            "[Hugging Face](https://huggingface.co/models)",
            "[Docs](http://localhost:8000/api)"
        ],
        "negative": [
            "[](https://google.com)",
            "[[nested]](https://google.com)",
            "[Google](ftp://google.com)",
            "[Google](https://google.com with spaces)",
            "[Google] (https://google.com)"
        ],
        "redos_payloads": [
            "[" + "text " * 25 + "](https://domain.com/path)"
        ],
        "canonical_ref": r"^\[([^\[\]\n]+)\]\((https?://[^\s\(\)]+)\)$"
    }
]


def get_problem_by_id(problem_id: str) -> Dict[str, Any]:
    for p in PROBLEMS:
        if p["id"] == problem_id:
            return p
    raise KeyError(f"Problem {problem_id} not found.")
