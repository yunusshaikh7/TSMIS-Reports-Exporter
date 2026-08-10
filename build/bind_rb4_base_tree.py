"""Bind the acceptance BASE tree to the base commit, by content.

`base-tree/` is a plain copy, not a checkout, so nothing tied it to
72adf447… — `counts-base.json` recorded `tree_commit: null` and the verifier's
`--tree` defaulted to the head repo, which would make base == head and every
count-invariance claim trivially true.

This compares the base tree's runtime files against the base commit's own git
blobs, byte for byte, and writes results/base-tree-binding.json. It is a hard
gate: any missing, extra, or differing file fails.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\Users\Yunus\Projects\wt-rb4")
ROOT = Path(r"C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes"
            r"\HF-05\rb4-a1")
BASE_TREE = ROOT / "base-tree"
BASE_COMMIT = "72adf447d45a2b74c562ba714008661a180c5d5f"
# The runtime the acceptance actually loads from the base tree.
BOUND_PREFIXES = ("scripts/", "version.py")


def git(*args):
    out = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: "
                         f"{out.stderr.decode(errors='replace')[:400]}")
    return out.stdout


def main():
    listing = git("ls-tree", "-r", "--name-only", BASE_COMMIT).decode()
    want = sorted(p for p in listing.splitlines()
                  if p.startswith(BOUND_PREFIXES))
    if not want:
        raise SystemExit("no runtime paths found at the base commit")

    # This repo is `core.autocrlf=true`: git stores LF and every checkout has
    # CRLF, so the base tree — a copy of a checkout — differs from the stored
    # blobs in exactly that way and no other. Line endings are therefore
    # compared and COUNTED, but the binding is on normalized content, which is
    # what the interpreter loads. A content difference is still a hard failure.
    matched, eol_only, differing, missing = [], [], [], []
    digest = hashlib.sha256()
    for rel in want:
        blob = git("show", f"{BASE_COMMIT}:{rel}")
        local = BASE_TREE / rel
        if not local.is_file():
            missing.append(rel)
            continue
        raw = local.read_bytes()
        norm = blob.replace(b"\r\n", b"\n")
        if raw == blob:
            matched.append(rel)
        elif raw.replace(b"\r\n", b"\n") == norm:
            eol_only.append(rel)
        else:
            differing.append({"path": rel, "how": "content",
                              "blob_sha256": hashlib.sha256(blob).hexdigest(),
                              "file_sha256": hashlib.sha256(raw).hexdigest()})
        digest.update(rel.encode() + b"\0" + hashlib.sha256(norm).digest())

    extra = sorted(
        str(p.relative_to(BASE_TREE)).replace("\\", "/")
        for p in (BASE_TREE / "scripts").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
        and str(p.relative_to(BASE_TREE)).replace("\\", "/") not in set(want))

    ok = not missing and not differing and not extra
    record = {"base_commit": BASE_COMMIT, "base_tree": str(BASE_TREE),
              "bound_prefixes": list(BOUND_PREFIXES),
              "files_compared": len(want),
              "identical_bytes": len(matched),
              "identical_content_crlf_checkout": len(eol_only),
              "missing": missing, "content_differences": differing,
              "extra": extra, "autocrlf": "true",
              "digest_over": "LF-normalized blob content",
              "base_runtime_digest": digest.hexdigest(), "bound": ok}
    out = ROOT / "results" / "base-tree-binding.json"
    out.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(f"base tree: {len(want)} runtime files vs {BASE_COMMIT[:7]} — "
          f"{len(matched)} byte-identical, {len(eol_only)} identical content "
          f"in the CRLF checkout form, {len(differing)} content differences")
    print(f"digest: {record['base_runtime_digest']}")
    if not ok:
        print(f"NOT BOUND — missing={len(missing)} "
              f"content_differences={len(differing)} extra={len(extra)}")
        for item in (missing + differing + extra)[:10]:
            print("  ", item)
        return 1
    print("BOUND")
    return 0


if __name__ == "__main__":
    sys.exit(main())
