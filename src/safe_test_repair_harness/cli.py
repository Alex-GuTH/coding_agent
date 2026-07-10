import argparse
import json

from safe_test_repair_harness.demo import feedback_classifier_demo, guardrail_demo, repair_loop_demo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="safe-repair",
        description="Safe Test-Repair Coding Harness",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="safe-repair 0.1.0",
    )
    subparsers = parser.add_subparsers(dest="command")
    demo_parser = subparsers.add_parser("demo", help="Run deterministic built-in demos")
    demo_subparsers = demo_parser.add_subparsers(dest="demo_name")
    guardrail_parser = demo_subparsers.add_parser("guardrail", help="Run guardrail blocking demo")
    guardrail_parser.set_defaults(demo_func=guardrail_demo)
    feedback_parser = demo_subparsers.add_parser(
        "feedback-classifier",
        help="Run deterministic feedback classifier demo",
    )
    feedback_parser.set_defaults(demo_func=feedback_classifier_demo)
    repair_parser = demo_subparsers.add_parser("repair-loop", help="Run mock repair-loop demo")
    repair_parser.set_defaults(demo_func=repair_loop_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    demo_func = getattr(args, "demo_func", None)
    if demo_func is not None:
        print(json.dumps(demo_func(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
