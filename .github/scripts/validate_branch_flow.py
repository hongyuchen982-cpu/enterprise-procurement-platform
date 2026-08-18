import re
import sys

DEVELOP_BRANCH = re.compile(r"(?:feature|fix)/(?:a|b)-[a-z0-9][a-z0-9._-]*")
MAIN_HOTFIX_BRANCH = re.compile(r"hotfix/(?:a|b)-[a-z0-9][a-z0-9._-]*")


def is_allowed_flow(base_ref: str, head_ref: str) -> bool:
    if base_ref == "develop":
        return DEVELOP_BRANCH.fullmatch(head_ref) is not None
    if base_ref == "main":
        return (
            head_ref == "develop" or MAIN_HOTFIX_BRANCH.fullmatch(head_ref) is not None
        )
    return False


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: validate_branch_flow.py BASE_REF HEAD_REF")
        return 2
    base_ref, head_ref = sys.argv[1:]
    if is_allowed_flow(base_ref, head_ref):
        return 0
    print(f"invalid pull-request flow: {head_ref} -> {base_ref}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
