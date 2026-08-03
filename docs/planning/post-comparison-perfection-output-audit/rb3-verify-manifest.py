"""Verify the `RB3-A1` acceptance manifest — read-only, and cheap.

Review 1 denied RB-3 (`RB3-R1-EG-001`) because the retained acceptance set was
a collection of separate claims: a head marker here, a generation record
there, output hashes in a sweep — with nothing binding the complete set to
ONE exact runtime head and the frozen inputs. `rb3-a1-artifacts.json` supplies
that binding. This script checks it.

It is deliberately an INDEPENDENT implementation: the runtime set is re-derived
straight out of `git`, the lineage claims are recomputed rather than believed,
and every committed witness must itself say which acceptance head it is bound
to. RB-2's review history also proved that runtime-DIGEST equality is not head
identity, so every claimed result here must name the ONE acceptance commit
exactly; a digest match alone never passes.

Checks, each reported separately:

  RUNTIME    re-derive the runtime set (scripts/, version.py,
             requirements.txt, build/) at any commit and compare per-file
             LF-normalized hashes and the rolled digest. Needs only the repo.
  LINEAGE    re-derive from git that the LAST commit touching any runtime
             file IS the acceptance head and nothing runtime-affecting
             happened after it.
  EXACT HEAD every claimed result/render/witness entry names the acceptance
             commit exactly; commits between it and the manifest build head
             touch no runtime file.
  WITNESSES  re-hash the four committed HF-04 witnesses and require each
             file's own content to carry `bound_to_acceptance_head` equal to
             the acceptance commit, with its producing script bound in the
             manifest's harness block.
  CORPUS     (--corpus) re-hash the frozen inputs, the provisioned replicas
             (each file must equal its recorded frozen source byte-for-byte),
             the deliverables, the retained results, and the harness. Bulk
             and local-only; SKIPPED, and reported as skipped, when a root is
             not present. (--zips additionally re-matches every Ramp Detail
             member of the two retained frozen archives against the recorded
             input hashes.)

Usage:
  rb3-verify-manifest.py <manifest.json> [--tree <repo>] [--at <commit>]
                         [--corpus] [--zips]
"""
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

GROUP_ROOTS = {"product": ("scripts", "version.py", "requirements.txt"),
               "gate": ("build",)}
SKIP_SUFFIXES = (".pyc", ".pyo")
SKIP_PARTS = ("__pycache__", ".ruff_cache", ".venv", "node_modules")
CHUNK = 1 << 20


def git(tree, *args):
    proc = subprocess.run(("git", "-C", str(tree)) + args, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: "
                         f"{proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc.stdout


def lf_sha(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest().upper()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest().upper()


def skipped(rel):
    return (rel.endswith(SKIP_SUFFIXES)
            or any(part in rel.split("/") for part in SKIP_PARTS))


def runtime_entries(tree, commit=None):
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
            entries[f"{group}/{rel}"] = lf_sha(data)
    return entries


def digest_of(entries):
    h = hashlib.sha256()
    for rel in sorted(entries):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(entries[rel].encode("ascii"))
        h.update(b"\n")
    return h.hexdigest().upper()


def check_runtime(manifest, tree, commit, fail):
    recorded = {f"{g}/{rel}": rec["sha256_lf"]
                for g, grp in manifest["runtime"]["head"]["files"].items()
                for rel, rec in grp.items()}
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
    only_d = sorted(set(derived) - set(recorded))
    only_r = sorted(set(recorded) - set(derived))
    diff = sorted(rel for rel in set(derived) & set(recorded)
                  if derived[rel] != recorded[rel])
    fail(f"the runtime set at {where} does not match the manifest: "
         f"{len(diff)} differ, {len(only_d)} extra, {len(only_r)} missing")
    for rel in (diff + only_d + only_r)[:20]:
        print(f"    {rel}")


def check_lineage(manifest, tree, fail):
    head = manifest["acceptance_head"]["commit"]
    lineage = manifest["runtime"].get("lineage") or {}
    roots = [r for grp in GROUP_ROOTS.values() for r in grp]
    print("\nLINEAGE — re-derived from git")

    def text(*args):
        return git(tree, *args).decode("utf-8", "replace")

    last = text("log", "-1", "--format=%H", "HEAD", "--", *roots).strip()
    if last != head:
        fail(f"the last runtime commit is {last[:12]}, not the acceptance "
             f"head {head[:12]} — runtime changed after the acceptance run")
        return
    print(f"  last runtime change IS the head    {last[:12]}")
    if str(lineage.get("runtime_last_changed_at")) != last:
        fail("the manifest's lineage does not record that commit")
        return
    touched = [f for f in text("diff", "--name-only", f"{head}..HEAD", "--",
                               *roots).splitlines() if f.strip()]
    if touched:
        fail(f"runtime files changed after {head[:12]}: {touched[:10]}")
        return
    if not lineage.get("runtime_unchanged_since_last_product_commit"):
        fail("the manifest does not assert the runtime is unchanged since "
             "the acceptance head, though it is")
        return
    print(f"  runtime files changed since        0")
    print(f"  non-runtime commits since          "
          f"{len(lineage.get('commits_since_on_head') or [])} recorded")


def check_exact_head(manifest, tree, fail):
    """Every claimed entry names ONE EXACT commit — digest equality is
    necessary and NOT sufficient (the RB-2 Review 2 lesson)."""
    head = (manifest.get("acceptance_head") or {}).get("commit")
    print("\nEXACT HEAD — one acceptance head for every claimed result")
    if not head:
        fail("the manifest names no acceptance head")
        return
    entries = manifest["results"]["entries"]
    claimed = [r for r in entries if r.get("class") == "acceptance"]
    missing = [r["path"] for r in claimed if not r.get("runtime_head_commit")]
    wrong = [(r["path"], r["runtime_head_commit"]) for r in claimed
             if r.get("runtime_head_commit")
             and r["runtime_head_commit"] != head]
    print(f"  acceptance head                    {head[:12]}")
    print(f"  claimed entries                    {len(claimed)}")
    for path in missing:
        fail(f"claimed entry names no exact head: {path}")
    for path, got in wrong:
        fail(f"claimed entry names {got[:12]}, not {head[:12]}: {path}")
    if not missing and not wrong:
        print("  all name the acceptance head       yes")
    if not manifest["results"].get("all_claimed_same_head", False):
        fail("the manifest does not assert that every claimed result is "
             "same-head")
    for key in ("off_head", "unstamped"):
        for path in manifest["results"].get(key) or ():
            fail(f"{key} result recorded: {path}")
    build = (manifest.get("acceptance_head") or {}).get("manifest_built_at")
    if build and build != head:
        roots = [r for grp in GROUP_ROOTS.values() for r in grp]
        touched = [f for f in git(tree, "diff", "--name-only",
                                  f"{head}..{build}", "--", *roots
                                  ).decode("utf-8", "replace").splitlines()
                   if f.strip()]
        between = [ln for ln in git(tree, "log", "--format=%h",
                                    f"{head}..{build}"
                                    ).decode().splitlines() if ln]
        print(f"  manifest built at                  {build[:12]} "
              f"({len(between)} commit(s) after the head)")
        if touched:
            fail(f"runtime files changed between the acceptance head and the "
                 f"manifest build head: {touched[:10]}")
        else:
            print("  runtime files changed in between   0")


def check_witnesses(manifest, tree, fail):
    head = manifest["acceptance_head"]["commit"]
    harness = manifest["harness"]["files"]
    entries = [r for r in manifest["results"]["entries"]
               if r.get("role") == "committed-witness"]
    print(f"\nWITNESSES — {len(entries)} committed record(s)")
    if not entries:
        fail("the manifest binds no committed witness")
        return
    for rec in entries:
        name = Path(rec["path"]).name
        local = next(Path(tree).glob(
            "docs/planning/post-comparison-perfection-output-audit/"
            f"hotfix-bundles/HF-04/witness/{name}"), None)
        if local is None:
            fail(f"{name}: not found in the repository")
            continue
        got = file_sha256(local)
        if got != rec["sha256"]:
            fail(f"{name}: sha256 {got[:16]}… != recorded "
                 f"{rec['sha256'][:16]}…")
            continue
        body = json.loads(local.read_text(encoding="utf-8"))
        bound = body.get("bound_to_acceptance_head")
        if bound != head:
            fail(f"{name}: bound to {str(bound)[:12]}, not the acceptance "
                 f"head — a committed witness must record which head it "
                 f"belongs to")
            continue
        producer = (body.get("produced_by") or {})
        script = producer.get("script")
        if not script or script not in harness or \
                producer.get("script_sha256") != harness[script]["sha256"]:
            fail(f"{name}: its producing script is not bound in the "
                 f"manifest's harness block")
            continue
        print(f"  ok  {name:<36} {rec['sha256'][:16]}…  bound to "
              f"{head[:12]}")


def rehash_block(label, root, recorded, fail, sources=None):
    root = Path(root)
    if not root.exists():
        print(f"  SKIPPED {label:<28} not present")
        return
    bad = 0
    for rel, want in recorded.items():
        p = root / rel
        if not p.is_file():
            bad += 1
            fail(f"{label}: missing {rel}")
            continue
        got = file_sha256(p)
        if got != want["sha256"]:
            bad += 1
            fail(f"{label}: content changed — {rel}")
            continue
        if sources is not None:
            src = sources.get(rel)
            if src is None or src["sha256"] != got:
                bad += 1
                fail(f"{label}: {rel} does not equal its frozen source")
    if not bad:
        print(f"  ok  {label:<28} {len(recorded):>5} file(s) re-hashed")


def check_corpus(manifest, fail, zips):
    print("\nCORPUS — frozen inputs, replicas, deliverables, results")
    fs = manifest["frozen_sources"]
    for row in fs["roots"]:
        rehash_block(row["label"], row["path"], fs["files"][row["label"]],
                     fail)
    raw = fs["tsn_raw"]
    p = Path(raw["path"])
    if p.is_file() and file_sha256(p) == raw["sha256"]:
        print(f"  ok  {'tsn-raw-master':<28}     1 file(s) re-hashed")
    elif p.is_file():
        fail("tsn-raw-master: content changed")
    else:
        print(f"  SKIPPED {'tsn-raw-master':<28} not present")
    reps = manifest["input_replicas"]
    for row in reps["roots"]:
        src = (fs["files"].get(row["copied_from"])
               or ({Path(raw["path"]).name: raw}
                   if row["copied_from"] == "tsn-raw-master" else {}))
        rehash_block(row["label"], row["path"], reps["files"][row["label"]],
                     fail, sources=src)
    if reps.get("mismatches"):
        fail(f"the manifest itself records replica mismatches: "
             f"{reps['mismatches'][:5]}")
    dl = manifest["deliverables"]
    for row in dl["roots"]:
        rehash_block(row["label"], row["path"], dl["files"][row["label"]],
                     fail)
    for rec in manifest["results"]["entries"]:
        p = Path(rec["path"])
        if rec.get("role") == "committed-witness":
            continue                      # checked against the repo above
        if not p.is_file():
            print(f"  SKIPPED result {p.name:<32} not present")
            continue
        if file_sha256(p) != rec["sha256"]:
            fail(f"result changed: {p}")
    print(f"  ok  results re-hashed              "
          f"{sum(1 for r in manifest['results']['entries'] if Path(r['path']).is_file())}")
    hz = manifest["harness"]
    loc = Path(hz["location"])
    rehash_block("harness", loc, {n: rec for n, rec in hz["files"].items()},
                 fail)
    if zips:
        print("  re-matching the frozen archives…")
        for b in fs["archive_bindings"]:
            zp = Path(b["archive"])
            if not zp.is_file():
                print(f"  SKIPPED archive {zp.name} not present")
                continue
            if file_sha256(zp) != b["sha256"]:
                fail(f"archive changed: {zp}")
                continue
            if b["mismatched"] or b["extract_files_not_in_archive"]:
                fail(f"the manifest itself records archive mismatches for "
                     f"{zp.name}")
                continue
            print(f"  ok  {zp.name:<28} {b['matched']:>5} member(s) bound")


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    manifest = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    tree = Path(".")
    commit = None
    corpus = zips = False
    i = 1
    while i < len(args):
        if args[i] == "--tree":
            tree = Path(args[i + 1]); i += 2
        elif args[i] == "--at":
            commit = args[i + 1]; i += 2
        elif args[i] == "--corpus":
            corpus = True; i += 1
        elif args[i] == "--zips":
            zips = True; i += 1
        else:
            raise SystemExit(f"unknown argument {args[i]}")

    failures = []

    def fail(message):
        failures.append(message)
        print(f"  FAIL {message}")

    print(f"manifest {manifest['id']} for bundle {manifest['bundle']}")
    print(f"  built            {manifest['built_utc']}")
    print(f"  acceptance head  {manifest['acceptance_head']['commit']}")
    print(f"  head runtime     "
          f"{manifest['runtime']['head']['runtime_digest']}")

    check_runtime(manifest, tree, commit, fail)
    check_lineage(manifest, tree, fail)
    check_exact_head(manifest, tree, fail)
    check_witnesses(manifest, tree, fail)
    if corpus:
        check_corpus(manifest, fail, zips)
    else:
        print("\nCORPUS — not requested (pass --corpus to re-hash it; "
              "--zips to re-match the frozen archives)")

    print(f"\n{'FAILED' if failures else 'VERIFIED'} — "
          f"{len(failures)} problem(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
