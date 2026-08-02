"""Verify the `RB2-A1` acceptance manifest — read-only, and cheap.

Review 1 denied RB-2 because its acceptance results were not bound to one exact
runtime: nothing in a retained result said which code produced it, so a corpus
built before the final shared-writer change could not be told apart from one
built after. The manifest supplies that binding. This script checks it.

It is deliberately an INDEPENDENT implementation. The manifest is written by the
acceptance harness; if this script re-used the harness's own digest code, the two
would agree by construction. The runtime-set digest is therefore recomputed here
from first principles, straight out of `git`, so a reviewer is checking the claim
rather than the claimant.

Three levels of check, each reported separately:

  RUNTIME    re-derive the runtime set at any commit and compare digests. This
             is what proves a later documentation-only commit did not change the
             code that produced the corpus. Needs only the repository.
  WITNESSES  re-hash every committed witness and confirm the runtime digest
             embedded in it is the manifest's head runtime. Needs only the
             repository.
  CORPUS     re-hash the frozen inputs, the produced deliverables and the
             retained results. Needs the local acceptance corpus, which is bulk
             output and is not committed; SKIPPED, and reported as skipped, when
             it is not present.

Usage:
  rb2-verify-manifest.py <manifest.json> [--tree <repo>] [--at <commit>]
                         [--sources <sources.json>] [--corpus]

`--at` re-derives the runtime set from a committed tree instead of the working
tree, which is how a reviewer checks the head from any later commit.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

# The same grouping the manifest records. Kept here as a literal, not imported,
# so a changed harness cannot quietly redefine what "runtime" means.
GROUP_ROOTS = {
    "product": ("scripts", "version.py", "requirements.txt"),
    "gate": ("build",),
    "oracle": ("docs/planning/post-comparison-perfection-output-audit/"
               "stage2-measure-clipping.py",),
}
SKIP_SUFFIXES = (".pyc", ".pyo")
SKIP_PARTS = ("__pycache__", ".ruff_cache", ".venv", "node_modules")
CHUNK = 1 << 20


def git(tree, *args):
    proc = subprocess.run(("git", "-C", str(tree)) + args, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: "
                         f"{proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc.stdout


def skipped(rel):
    return (rel.endswith(SKIP_SUFFIXES)
            or any(part in rel.split("/") for part in SKIP_PARTS))


def normalised_sha256(data):
    """CRLF -> LF before hashing: this repository runs core.autocrlf=true, so the
    same commit checks out with different bytes on different platforms while the
    CONTENT — which is what decides behaviour — is identical."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest().upper()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest().upper()


def runtime_entries(tree, commit=None):
    """The runtime set and its per-file content hashes, from git."""
    entries = {}
    for group, roots in GROUP_ROOTS.items():
        if commit:
            listing = git(tree, "ls-tree", "-r", "--name-only", "-z", commit,
                          "--", *roots)
        else:
            listing = git(tree, "ls-files", "-z", "--", *roots)
        for rel in listing.decode("utf-8").split("\0"):
            if not rel or skipped(rel):
                continue
            if commit:
                data = git(tree, "show", f"{commit}:{rel}")
            else:
                full = Path(tree) / rel
                if not full.is_file():
                    continue
                data = full.read_bytes()
            entries[f"{group}/{rel}"] = normalised_sha256(data)
    return entries


def digest_of(entries):
    h = hashlib.sha256()
    for rel in sorted(entries):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(entries[rel].encode("ascii"))
        h.update(b"\n")
    return h.hexdigest().upper()


def manifest_runtime_entries(manifest):
    """Flatten the manifest's recorded head runtime into the same shape."""
    files = manifest["runtime"]["head"]["files"]
    return {f"{group}/{rel}": rec["sha256_lf"]
            for group, group_files in files.items()
            for rel, rec in group_files.items()}


def check_runtime(manifest, tree, commit, fail):
    recorded = manifest_runtime_entries(manifest)
    claimed = manifest["runtime"]["head"]["runtime_digest"]
    where = commit or "working tree"
    print(f"\nRUNTIME — re-derived from {where}")
    if digest_of(recorded) != claimed:
        fail(f"the manifest's own file list digests to {digest_of(recorded)}, "
             f"but it claims {claimed}")
        return
    print(f"  manifest self-consistent           {claimed}")
    derived = runtime_entries(tree, commit)
    if derived == recorded:
        print(f"  re-derived digest MATCHES          {digest_of(derived)}")
        print(f"  files compared                     {len(derived)}")
        return
    only_derived = sorted(set(derived) - set(recorded))
    only_recorded = sorted(set(recorded) - set(derived))
    differing = sorted(rel for rel in set(derived) & set(recorded)
                       if derived[rel] != recorded[rel])
    fail(f"the runtime set at {where} does not match the manifest: "
         f"{len(differing)} file(s) differ, {len(only_derived)} extra, "
         f"{len(only_recorded)} missing")
    for rel in (differing + only_derived + only_recorded)[:20]:
        print(f"    {rel}")


def check_lineage(manifest, tree, commit, fail):
    """Re-derive the manifest's central claim instead of believing it.

    The manifest asserts that the last commit touching any runtime file is the
    final production commit, and that nothing runtime-affecting happened after
    it — which is what makes a corpus generated at a LATER head still
    same-final-head. Taken from the manifest that is worth nothing, so it is
    computed here from Git independently.
    """
    lineage = manifest["runtime"].get("lineage") or {}
    print("\nLINEAGE — re-derived from git")
    if not lineage:
        fail("the manifest records no runtime lineage")
        return
    roots = [r for group in GROUP_ROOTS.values() for r in group]
    head = commit or "HEAD"

    def text(*args):
        # git() returns BYTES here; decode explicitly as UTF-8 rather than the
        # locale codepage, which mangles the em dashes in this repo's subjects.
        return git(tree, *args).decode("utf-8", "replace")

    last = text("log", "-1", "--format=%H", head, "--", *roots).strip()
    recorded = str(lineage.get("runtime_last_changed_at") or "")
    if last != recorded:
        fail(f"last runtime commit is {last[:12]}, manifest says "
             f"{recorded[:12] or '(none)'}")
        return
    print(f"  last runtime change                {last[:12]}")
    changed = [f for f in text("diff", "--name-only", f"{last}..{head}",
                               "--", *roots).splitlines() if f.strip()]
    if changed:
        fail(f"runtime files changed after {last[:12]}: {changed[:10]}")
        return
    if not lineage.get("runtime_unchanged_since_last_product_commit"):
        fail("the manifest does not assert the runtime is unchanged since its "
             "last product commit, though it is")
        return
    since = lineage.get("commits_since_on_head") or []
    print(f"  runtime files changed since        0")
    print(f"  non-runtime commits since          {len(since)}")


def check_exact_head(manifest, tree, fail):
    """Every claimed result must name ONE EXACT Git head — not merely an equal
    runtime digest.

    This check exists because its absence was the finding. The first verifier
    compared only runtime digests, and a digest is content-derived: a set split
    across two commits with byte-identical runtime content produced equal
    digests and passed, while actually spanning two heads. Digest equality is
    necessary and NOT sufficient.

    The intervening commits are re-derived from git here rather than read from
    the manifest, so the explanation for any gap between the acceptance head and
    the manifest's own build head is checked, not accepted.
    """
    block = manifest.get("acceptance_head") or {}
    head = block.get("commit")
    print("\nEXACT HEAD — one acceptance head for every claimed result")
    if not head:
        fail("the manifest names no acceptance head")
        return
    claimed = [r for r in manifest["results"]["entries"]
               if r.get("class", "acceptance") == "acceptance"]
    missing = [r["path"] for r in claimed if not r.get("runtime_head_commit")]
    mismatched = [(r["path"], r["runtime_head_commit"]) for r in claimed
                  if r.get("runtime_head_commit")
                  and r["runtime_head_commit"] != head]
    print(f"  acceptance head                    {head[:12]}")
    print(f"  claimed results                    {len(claimed)}")
    for path in missing:
        fail(f"claimed result names no exact head: {path}")
    for path, got in mismatched:
        fail(f"claimed result names {got[:12]}, not the acceptance head "
             f"{head[:12]}: {path}")
    if not missing and not mismatched:
        print(f"  all name the acceptance head       yes")

    # The manifest is committed after the run it describes, so its own build
    # head may legitimately be later. Re-derive what came between and confirm
    # none of it is a runtime file.
    build = block.get("manifest_built_at")
    if build and build != head:
        roots = [r for group in GROUP_ROOTS.values() for r in group]
        between = [ln for ln in git(tree, "log", "--format=%h %s",
                                    f"{head}..{build}").decode("utf-8", "replace"
                                                               ).splitlines() if ln]
        touched = [f for f in git(tree, "diff", "--name-only", f"{head}..{build}",
                                  "--", *roots).decode("utf-8", "replace"
                                                       ).splitlines() if f.strip()]
        print(f"  manifest built at                  {build[:12]}")
        print(f"  commits in between                 {len(between)}")
        if touched:
            fail(f"runtime files changed between the acceptance head and the "
                 f"manifest build head: {touched[:10]}")
        else:
            print(f"  runtime files changed in between   0")


def check_witnesses(manifest, tree, fail):
    head_digest = manifest["runtime"]["head"]["runtime_digest"]
    entries = [rec for rec in manifest["results"]["entries"]
               if "hotfix-bundles" in rec["path"].replace("\\", "/")]
    print(f"\nWITNESSES — {len(entries)} committed record(s)")
    if not entries:
        fail("the manifest binds no committed witness")
        return
    for rec in entries:
        name = Path(rec["path"]).name
        local = None
        for candidate in Path(tree).rglob(f"hotfix-bundles/**/{name}"):
            local = candidate
            break
        if local is None:
            fail(f"{name}: not found in the repository")
            continue
        got = file_sha256(local)
        if got != rec["sha256"]:
            fail(f"{name}: sha256 {got} != recorded {rec['sha256']}")
            continue
        stamp = rec.get("runtime_digest")
        # An UNSTAMPED committed witness must fail. Accepting one as "distilled"
        # is exactly the condition Review 1 denied RB-2 for, so a verifier that
        # waved it through would certify the gap it exists to catch.
        if not stamp:
            fail(f"{name}: carries no runtime stamp — a committed witness must "
                 f"record which runtime produced it")
            continue
        if stamp != head_digest:
            fail(f"{name}: produced under runtime {stamp}, not the head runtime")
            continue
        print(f"  ok  {name:<34} {rec['sha256'][:16]}…  same-head")


def check_corpus(manifest, sources_path, fail):
    print("\nCORPUS — bulk acceptance output")
    roots = (manifest["deliverables"]["roots"]
             + manifest["frozen_sources"]["roots"])
    present = [row for row in roots if Path(row["path"]).exists()]
    if not present:
        print("  SKIPPED — the local acceptance corpus is not on this machine")
        return
    files_by_root = manifest["deliverables"]["files"]
    if sources_path and Path(sources_path).exists():
        source_files = json.loads(
            Path(sources_path).read_text(encoding="utf-8"))["roots"]
        got = file_sha256(sources_path)
        want = manifest["frozen_sources"].get("listing_sha256")
        if want and got != want:
            fail(f"the frozen-source listing hashes to {got}, "
                 f"but the manifest records {want}")
        else:
            print(f"  ok  frozen-source listing bound       {got[:16]}…")
        for label, rec in source_files.items():
            files_by_root[label] = rec
    for row in roots:
        root = Path(row["path"])
        if not root.exists():
            print(f"  SKIPPED {row['label']:<22} not present")
            continue
        recorded = (files_by_root.get(row["label"]) or {}).get("files")
        if recorded is None:
            print(f"  SKIPPED {row['label']:<22} no per-file listing supplied")
            continue
        bad = 0
        for rel, want in recorded.items():
            path = root / rel
            if not path.is_file():
                bad += 1
                fail(f"{row['label']}: missing {rel}")
                continue
            if "sha256" in want and file_sha256(path) != want["sha256"]:
                bad += 1
                fail(f"{row['label']}: content changed — {rel}")
        if not bad:
            print(f"  ok  {row['label']:<22} {len(recorded):>6} file(s) "
                  f"re-hashed")


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    manifest_path = Path(args[0])
    tree = Path(".")
    commit = sources = None
    corpus = False
    i = 1
    while i < len(args):
        if args[i] == "--tree":
            tree = Path(args[i + 1]); i += 2
        elif args[i] == "--at":
            commit = args[i + 1]; i += 2
        elif args[i] == "--sources":
            sources = args[i + 1]; i += 2
        elif args[i] == "--corpus":
            corpus = True; i += 1
        else:
            raise SystemExit(f"unknown argument {args[i]}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []

    def fail(message):
        failures.append(message)
        print(f"  FAIL {message}")

    head = manifest["runtime"]["head"].get("git") or {}
    print(f"manifest {manifest['id']} for bundle {manifest['bundle']}")
    print(f"  built            {manifest['built_utc']}")
    print(f"  head commit      {head.get('head')}  clean={head.get('clean')}")
    print(f"  head runtime     "
          f"{manifest['runtime']['head']['runtime_digest']}")

    check_runtime(manifest, tree, commit, fail)
    check_lineage(manifest, tree, commit, fail)
    check_exact_head(manifest, tree, fail)
    check_witnesses(manifest, tree, fail)
    if corpus:
        check_corpus(manifest, sources, fail)
    else:
        print("\nCORPUS — not requested (pass --corpus to re-hash it)")

    results = manifest["results"]
    for path in results.get("off_head") or ():
        fail(f"result produced under a different runtime: {path}")
    # A CLAIMED result with no stamp at all is the same defect as an off-head
    # one, and was previously unchecked.
    for path in results.get("unstamped") or ():
        fail(f"claimed result carries no runtime stamp: {path}")
    for path in results.get("base_side_mislabelled") or ():
        fail(f"base-side result not produced by the base runtime: {path}")
    # Require the claim to be MADE. Without this, a manifest that simply omitted
    # the field would verify clean by saying nothing.
    if not results.get("all_claimed_same_head", False):
        fail("the manifest does not assert that every claimed result is "
             "same-head")
    print(f"\n{'FAILED' if failures else 'VERIFIED'} — "
          f"{len(failures)} problem(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
