# PackBridge golden benchmark

This directory contains small, non-sensitive packing-list examples for repeatable local-model regression testing.

Each case contains source.txt (the extracted document text) and expected.json (the minimum canonical facts that must be recovered).

Run on the PackBridge host:

    flask --app wsgi:application packbridge benchmark --model qwen3:14b
    flask --app wsgi:application packbridge benchmark --model qwen3:8b

Results are written as JSON and can be compared between models.

The synthetic examples do not replace the controlled real-vendor acceptance set. Real supplier examples should be added only when safe to retain and after their expected canonical JSON has been manually approved.
