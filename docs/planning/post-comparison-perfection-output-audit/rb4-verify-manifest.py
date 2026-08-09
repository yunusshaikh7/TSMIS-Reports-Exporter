"""Verify the `RB4-A1` acceptance manifest — read-only, and cheap by default.

RB-3's model (one exact runtime head binding the complete set), with the RB-4
extensions the bundle's acceptance demanded:

  * SELF-STAMPS — every claimed head-side result was produced by a driver that
    stamps the tree's own `git rev-parse HEAD` and a runtime-scoped dirty flag
    INTO the result file. The manifest's assertion is re-checked against each
    file's own content (--corpus), so exact-head identity does not rest on the
    manifest builder alone (the RB-2 lesson: digest equality is not identity).
  * BASE TREE — the pre-fix defect signatures ran against a `git archive`
    export of the recorded base commit; the runtime set at that commit is
    re-derived from git and its digest compared, so the red half of red→green
    binds to an exact runtime too.
  * AUDIT SETS — the defect census recounted the output audit's retained
    evidence sets; each recounted file is bound to the Stage 1B witness
    MANIFEST (same path, same sha), proving the census measured the same bytes
    the audit measured.
  * DETACHED INVENTORY — the tens of thousands of per-file hashes live in
    `rb4-a1-inventory.json` beside the results, sha256-bound here. --corpus
    verifies the inventory's own digest before trusting one record from it,
    and every rolled per-root digest in this manifest is re-derived from it.

Checks, each reported separately:

  PROBLEMS   the manifest's OWN build problem list must be empty — always, not
             only under --corpus. A builder that recorded broken evidence has
             already failed the acceptance; the verifier may not certify it.
  RUNTIME    re-derive the runtime set (scripts/, version.py,
             requirements.txt, build/) at the acceptance head and compare
             per-file LF-normalized hashes and the rolled digest.
  LINEAGE    the LAST commit touching any runtime file IS the acceptance head
             and nothing runtime-affecting happened after it.
  EXACT HEAD every claimed entry names the acceptance commit exactly, the
             manifest's recorded self-stamps agree, and commits between the
             head and the manifest build head touch no runtime file. A
             manifest that claims NO acceptance result fails.
  BASE TREE  re-derive the runtime set at the recorded base commit; its digest
             must equal the manifest's `runtime_digest_at_base` and the
             manifest must assert the export matched file-for-file. The base
             side must be EXPLICITLY BOUND: the base commit may not be the
             acceptance head, the base export may not be the head tree, and
             every base-signature result must name the base commit in its own
             recorded stamp (a null/absent stamp fails — a driver run with the
             tree argument forgotten produces "base" results off the HEAD, and
             base<->head count invariance is then trivially true).
  WITNESSES  re-hash every committed witness (HF-05 + HF-10) from the repo and
             require each file's own content to carry
             `bound_to_acceptance_head` equal to the acceptance commit, with
             its producing script bound in the manifest's harness block.
  CORPUS     (--corpus) verify the detached inventory's digest, then re-hash
             the frozen inputs, the audit sets (re-matched against the Stage
             1B witness manifest), the provisioned replicas (each equal to its
             recorded hash AND its frozen source's hash), the deliverables,
             the retained results (re-reading each claimed result's own
             self-stamp, and each base result's own base stamp), and the
             harness. FAIL-CLOSED: once requested, every declared root, file,
             result and harness record MUST be present and match; any absence
             is a nonzero failure, never a skip. An EMPTY declaration — a root
             list with no roots, or a root with no files — fails too: it
             verifies nothing while reporting success.
  ZIPS       (--zips) re-match every ground-truth 7.9 member of the frozen
             archives against the inventory hashes; no ground-truth file may
             be outside every archive.
  SELF-TEST  (--self-test) bounded NEGATIVE checks over fabricated fixtures:
             a missing declared root/file/result, an EMPTY declared set,
             changed bytes, a replica diverging from its frozen source, a
             tampered detached inventory, a non-empty manifest problem list, a
             wrong-head / unstamped / dirty-stamped claimed entry, a manifest
             with no claimed entry at all, an unbound base side, and an
             unbound witness must each FAIL; a clean fixture must verify. The
             cases drive the REAL check functions (`check_exact_head`,
             `check_base_binding`, `check_witnesses`, `rehash_block`,
             `load_inventory`) — a self-test that reimplements the logic it is
             testing proves only that the copy works. Exits nonzero if any
             negative case passes.

Usage:
  rb4-verify-manifest.py <manifest.json> [--tree <repo>] [--corpus] [--zips]
  rb4-verify-manifest.py --self-test
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
SELF_STAMPED_ROLES = ("generate", "cameras", "counts", "validate", "excel")
BASE_SIGNATURE_CLASS = "base-signature"


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


def runtime_entries(tree, commit):
    entries = {}
    for group, roots in GROUP_ROOTS.items():
        listing = git(tree, "ls-tree", "-r", "--name-only", "-z", commit,
                      "--", *roots)
        for rel in listing.decode("utf-8").split("\0"):
            if not rel or skipped(rel):
                continue
            entries[f"{group}/{rel}"] = lf_sha(git(tree, "show",
                                                   f"{commit}:{rel}"))
    return entries


def digest_of(entries):
    h = hashlib.sha256()
    for rel in sorted(entries):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(entries[rel].encode("ascii"))
        h.update(b"\n")
    return h.hexdigest().upper()


def rolled_digest(files):
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(files[rel]["sha256"].encode("ascii"))
        h.update(b"\n")
    return h.hexdigest().upper()


def check_manifest_problems(manifest, fail):
    """The builder's own problem list is a VERDICT, not a footnote.

    It used to be read only under --corpus, so the cheap default run certified
    a manifest that said in its own body that it had been built over broken
    evidence. An absent list fails too: the builder always writes one, so a
    manifest without it is not a manifest this verifier can read."""
    print("\nPROBLEMS — the manifest's own build record")
    problems = manifest.get("problems")
    if problems is None:
        fail("the manifest records no 'problems' list — an absent list is not "
             "an empty one")
        return
    if problems:
        fail(f"the manifest itself records {len(problems)} build problem(s): "
             f"{problems[:3]}")
        return
    print("  builder recorded                   0 problem(s)")


def declared_roots(section, rows, fail):
    """The declared root list for one section. An EMPTY list fails for the same
    reason an empty file set does: nothing is verified and the run still
    reports success."""
    if not rows:
        fail(f"{section}: the manifest declares NO root — an empty declaration "
             f"verifies nothing")
        return ()
    return rows


def check_runtime(manifest, tree, fail):
    head = manifest["acceptance_head"]["commit"]
    recorded = {f"{g}/{rel}": rec["sha256_lf"]
                for g, grp in manifest["runtime"]["head"]["files"].items()
                for rel, rec in grp.items()}
    claimed = manifest["runtime"]["head"]["runtime_digest"]
    print(f"\nRUNTIME — re-derived from {head[:12]}")
    if digest_of(recorded) != claimed:
        fail(f"the manifest's own file list digests to {digest_of(recorded)}, "
             f"but it claims {claimed}")
        return
    print(f"  manifest self-consistent           {claimed}")
    derived = runtime_entries(tree, head)
    if derived == recorded:
        print(f"  re-derived digest MATCHES          {digest_of(derived)}")
        print(f"  files compared                     {len(derived)}")
        return
    only_d = sorted(set(derived) - set(recorded))
    only_r = sorted(set(recorded) - set(derived))
    diff = sorted(rel for rel in set(derived) & set(recorded)
                  if derived[rel] != recorded[rel])
    fail(f"the runtime set at {head[:12]} does not match the manifest: "
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
    print("  runtime files changed since        0")
    print(f"  non-runtime commits since          "
          f"{len(lineage.get('commits_since_on_head') or [])} recorded")


def stamp_problems(rec, head):
    """The manifest-recorded self-stamp problems for one claimed entry."""
    out = []
    if rec.get("role") in SELF_STAMPED_ROLES:
        stamp = rec.get("self_stamp") or {}
        if stamp.get("tree_commit") != head:
            out.append(f"self-stamp names {str(stamp.get('tree_commit'))[:12]}"
                       f", not the head: {rec['path']}")
        if stamp.get("tree_runtime_dirty") is not False:
            out.append(f"self-stamp does not record a CLEAN runtime tree: "
                       f"{rec['path']}")
    return out


def check_exact_head(manifest, tree, fail):
    """Every claimed entry names ONE EXACT commit and carries a clean
    self-stamp — digest equality is necessary and NOT sufficient."""
    head = (manifest.get("acceptance_head") or {}).get("commit")
    print("\nEXACT HEAD — one acceptance head for every claimed result")
    if not head:
        fail("the manifest names no acceptance head")
        return
    entries = manifest["results"]["entries"]
    claimed = [r for r in entries if r.get("class") == "acceptance"]
    if not claimed:
        # Nothing claimed means nothing was bound to the head, and every loop
        # below is vacuously satisfied.
        fail("the manifest claims NO acceptance result — there is nothing "
             "bound to the acceptance head")
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
    stamped = 0
    for rec in claimed:
        problems = stamp_problems(rec, head)
        for p in problems:
            fail(p)
        stamped += rec.get("role") in SELF_STAMPED_ROLES and not problems
    print(f"  clean self-stamps recorded         {stamped}")
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


def base_own_stamp(body):
    """The base commit a base-side result names for ITSELF, or None.

    Two spellings are legitimate and the manifest builder reads both: a
    single-tree base phase self-stamps `tree_commit`, while checks-at-base runs
    the HEAD's check files AGAINST the base tree and therefore names both sides
    explicitly (`base_tree_commit` / `head_tree_commit`). The head spelling is
    deliberately NOT consulted — falling back to it is exactly the substitution
    the base-binding checks exist to catch, and it would turn an unbound base
    side into a silent pass."""
    return body.get("tree_commit") or body.get("base_tree_commit")


def base_stamp_problems(rec, base_commit, head, export_path):
    """The manifest-recorded base stamp problems for one base-signature entry.

    The base side must name its OWN runtime the same way the head side does.
    A base result that names nothing — `tree_commit: null` — leaves the whole
    red half unbound: the acceptance driver's tree argument DEFAULTS to the
    head worktree, so a forgotten flag silently produces "base" results off the
    head runtime and every base<->head count then matches trivially."""
    out = []
    stamp = rec.get("base_stamp") or {}
    got = stamp.get("tree_commit")
    if not got:
        out.append(f"base-side result names NO runtime commit of its own "
                   f"(tree_commit={got!r}) — the base side is unbound: "
                   f"{rec['path']}")
    elif got == head:
        out.append(f"base-side result self-stamps the ACCEPTANCE HEAD "
                   f"{str(head)[:12]} — it did not run against the base "
                   f"runtime: {rec['path']}")
    elif got != base_commit:
        out.append(f"base-side result self-stamps {str(got)[:12]}, not the "
                   f"base commit {str(base_commit)[:12]}: {rec['path']}")
    ran_in = stamp.get("tree")
    if export_path and ran_in and Path(ran_in) != Path(export_path):
        out.append(f"base-side result ran in {ran_in}, not the recorded base "
                   f"export {export_path}: {rec['path']}")
    return out


def check_base_binding(manifest, fail):
    """The base side is bound EXPLICITLY or not at all: a distinct commit, a
    distinct tree, and base results that name that commit themselves."""
    base = manifest.get("base_tree") or {}
    commit = base.get("commit")
    head = (manifest.get("acceptance_head") or {}).get("commit")
    if commit == head:
        fail(f"the base commit IS the acceptance head {str(head)[:12]} — "
             f"invariance measured over one runtime proves nothing")
    export = base.get("export_path")
    head_tree = ((manifest.get("runtime") or {}).get("head") or {}).get("tree")
    if not export:
        fail("the manifest records no base tree export path")
    elif head_tree and Path(export) == Path(head_tree):
        fail(f"the base export path IS the head tree ({export}) — the base "
             f"side ran against the head runtime")
    entries = [r for r in manifest["results"]["entries"]
               if r.get("class") == BASE_SIGNATURE_CLASS]
    if not entries:
        fail("the manifest binds no base-signature result — the red half of "
             "red→green rests on nothing")
        return
    bound = 0
    for rec in entries:
        problems = base_stamp_problems(rec, commit, head, export)
        for p in problems:
            fail(p)
        bound += not problems
    print(f"  base results explicitly bound      {bound}/{len(entries)}")


def check_base_tree(manifest, tree, fail):
    base = manifest.get("base_tree") or {}
    commit = base.get("commit")
    print("\nBASE TREE — the pre-fix signatures' exact runtime")
    if not commit:
        fail("the manifest records no base commit")
        return
    derived = digest_of(runtime_entries(tree, commit))
    if derived != base.get("runtime_digest_at_base"):
        fail(f"the runtime digest at the base commit is {derived}, the "
             f"manifest records {base.get('runtime_digest_at_base')}")
        return
    print(f"  base commit                        {commit[:12]}")
    print(f"  re-derived base digest MATCHES     {derived}")
    if not base.get("export_matches_commit"):
        fail("the manifest does not assert the exported base tree matched "
             "the base commit")
    else:
        print(f"  export matched file-for-file       "
              f"{base.get('files_compared')} file(s) at build time")


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
        repo_rel = rec.get("repo_path")
        if not repo_rel:
            fail(f"{name}: no repo path recorded")
            continue
        local = Path(tree) / repo_rel
        if not local.is_file():
            fail(f"{name}: not found in the repository at {repo_rel}")
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
        print(f"  ok  {name:<44} {rec['sha256'][:16]}…")


def rehash_block(label, root, recorded, fail, sources=None):
    """Re-hash one declared root. FAIL-CLOSED: when the caller requested this
    verification, an ABSENT declared root or file is a failure, never a skip —
    a verifier that succeeds with declared evidence removed certifies an
    incomplete acceptance set. An EMPTY declaration is the same defect one
    level up: a root with no files re-hashes nothing and reported `ok`."""
    if not recorded:
        fail(f"{label}: the manifest declares an EMPTY file set — an empty "
             f"declaration verifies nothing")
        return
    root = Path(root)
    if not root.exists():
        fail(f"{label}: declared root is MISSING: {root}")
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
            if src is None or src != got:
                bad += 1
                fail(f"{label}: {rel} does not equal its frozen source")
    if not bad:
        print(f"  ok  {label:<34} {len(recorded):>6} file(s) re-hashed")


def load_inventory(manifest, fail):
    inv_rec = manifest.get("inventory") or {}
    p = Path(inv_rec.get("path", ""))
    if not p.is_file():
        fail(f"detached inventory MISSING: {p}")
        return None
    if file_sha256(p) != inv_rec.get("sha256"):
        fail("detached inventory does not match its recorded sha256 — "
             "nothing in it can be trusted")
        return None
    print(f"  inventory verified                 {inv_rec['sha256'][:16]}… "
          f"({inv_rec.get('bytes', 0):,} bytes)")
    return json.loads(p.read_text(encoding="utf-8"))


def check_corpus(manifest, tree, fail):
    print("\nCORPUS — frozen inputs, audit sets, replicas, deliverables, "
          "results (fail-closed: absence is a failure)")
    # The manifest's own problem list is checked unconditionally in main().
    inv = load_inventory(manifest, fail)
    if inv is None:
        return
    head = manifest["acceptance_head"]["commit"]

    fs = manifest["frozen_sources"]
    for row in declared_roots("frozen_sources", fs["roots"], fail):
        files = inv["frozen_files"].get(row["label"])
        if files is None:
            fail(f"{row['label']}: absent from the inventory")
            continue
        want = fs["summary"].get(row["label"], {}).get("rolled_sha256")
        if rolled_digest(files) != want:
            fail(f"{row['label']}: inventory does not match the manifest's "
                 f"rolled digest")
            continue
        rehash_block(row["label"], row["path"], files, fail)

    audit = fs["audit_sets"]
    wm_path = Path(audit["witness_manifest"]["path"])
    if not wm_path.is_file():
        fail(f"Stage 1B witness manifest MISSING: {wm_path}")
        witness_by_path = {}
    elif file_sha256(wm_path) != audit["witness_manifest"]["sha256"]:
        fail("Stage 1B witness manifest changed since the build")
        witness_by_path = {}
    else:
        witness_by_path = {str(Path(e["path"])): e["sha256"].upper()
                           for e in json.loads(
                               wm_path.read_text(encoding="utf-8"))}
    if audit.get("witness_mismatches"):
        fail(f"the manifest records audit/witness mismatches: "
             f"{audit['witness_mismatches'][:3]}")
    for row in declared_roots("audit_sets", audit["roots"], fail):
        files = inv["audit_files"].get(row["label"])
        if files is None:
            fail(f"{row['label']}: absent from the inventory")
            continue
        want = fs["audit_summary"].get(row["label"], {}).get("rolled_sha256")
        if rolled_digest(files) != want:
            fail(f"{row['label']}: inventory does not match the manifest's "
                 f"rolled digest")
            continue
        rehash_block(row["label"], row["path"], files, fail)
        if witness_by_path:
            unmatched = [rel for rel, rec in files.items()
                         if witness_by_path.get(
                             str(Path(row["path"]) / rel)) != rec["sha256"]
                         and rec.get("in_witness")]
            for rel in unmatched[:10]:
                fail(f"{row['label']}: {rel} no longer matches the Stage 1B "
                     f"witness hash")

    frozen_by_abs = {}
    for row in fs["roots"]:
        files = inv["frozen_files"].get(row["label"]) or {}
        for rel, rec in files.items():
            frozen_by_abs[str(Path(row["path"]) / rel)] = rec["sha256"]
    reps = manifest["input_replicas"]
    if reps.get("mismatches"):
        fail(f"the manifest itself records replica mismatches: "
             f"{reps['mismatches'][:5]}")
    for row in declared_roots("input_replicas", reps["roots"], fail):
        files = inv["replica_files"].get(row["label"])
        if files is None:
            fail(f"{row['label']}: absent from the inventory")
            continue
        want = reps["summary"].get(row["label"], {}).get("rolled_sha256")
        if rolled_digest(files) != want:
            fail(f"{row['label']}: inventory does not match the manifest's "
                 f"rolled digest")
            continue
        sources = {rel: frozen_by_abs.get(str(Path(rec["source"])))
                   for rel, rec in files.items()}
        rehash_block(row["label"], row["path"], files, fail, sources=sources)

    dl = manifest["deliverables"]
    for row in declared_roots("deliverables", dl["roots"], fail):
        files = inv["deliverable_files"].get(row["label"])
        if files is None:
            fail(f"{row['label']}: absent from the inventory")
            continue
        want = dl["summary"].get(row["label"], {}).get("rolled_sha256")
        if rolled_digest(files) != want:
            fail(f"{row['label']}: inventory does not match the manifest's "
                 f"rolled digest")
            continue
        rehash_block(row["label"], row["path"], files, fail)

    present = 0
    for rec in manifest["results"]["entries"]:
        if rec.get("role") in ("committed-witness", "inventory"):
            continue                      # witnesses repo-checked; inv above
        p = Path(rec["path"])
        if not p.is_file():
            fail(f"result MISSING: {p}")
            continue
        if file_sha256(p) != rec["sha256"]:
            fail(f"result changed: {p}")
            continue
        if rec.get("class") == "acceptance" and \
                rec.get("role") in SELF_STAMPED_ROLES:
            body = json.loads(p.read_text(encoding="utf-8"))
            if body.get("tree_commit") != head:
                fail(f"result's OWN self-stamp is not the head: {p}")
                continue
            if body.get("tree_runtime_dirty") is not False:
                fail(f"result's OWN self-stamp is not a clean runtime: {p}")
                continue
        if rec.get("class") == BASE_SIGNATURE_CLASS:
            # The same own-content re-read for the red half: the manifest's
            # recorded base stamp must be what the file itself says.
            #
            # `base_own_stamp` reads the two legitimate spellings and never the
            # head's field; accepting only `tree_commit` failed a correctly
            # bound checks-at-base result.
            body = json.loads(p.read_text(encoding="utf-8"))
            stamp = rec.get("base_stamp") or {}
            own = base_own_stamp(body)
            if not own:
                fail(f"base result names NO runtime commit of its own: {p}")
                continue
            if own != stamp.get("tree_commit"):
                fail(f"base result's OWN stamp {own!r} disagrees with the "
                     f"manifest's {stamp.get('tree_commit')!r}: {p}")
                continue
        present += 1
    expected = sum(1 for r in manifest["results"]["entries"]
                   if r.get("role") not in ("committed-witness", "inventory"))
    print(f"  results re-hashed                  {present}/{expected}")

    hz = manifest["harness"]
    rehash_block("harness", Path(hz["location"]),
                 {n: rec for n, rec in hz["files"].items()}, fail)
    driver = hz.get("driver") or {}
    if driver:
        got = lf_sha(git(tree, "show", f"{head}:{driver['repo_path']}"))
        if got != driver["sha256_lf"]:
            fail(f"the committed driver at the head does not match the "
                 f"manifest: {driver['repo_path']}")
        else:
            print(f"  ok  driver at head                 {driver['repo_path']}")


def archive_member_key(name):
    """Normalize one zip member path to the `<pull-dir-name>/<rel>` form the
    ground-truth folders use — the same mapping the manifest builder used:
    `All Reports 7.9.zip` nests everything under one 'All Reports 7.9/'
    segment; `ramp_summary_excel.zip` holds the ssor pull's ramp_summary_excel
    subdir directly."""
    name = name.replace("\\", "/")
    if name.startswith("All Reports 7.9/"):
        return name.split("/", 1)[1]
    return name


def check_zips(manifest, fail):
    print("\nZIPS — re-matching the frozen archives")
    inv = load_inventory(manifest, fail)
    if inv is None:
        return
    fs = manifest["frozen_sources"]
    by_key, ssor_name = {}, None
    for row in fs["roots"]:
        if row["label"] not in ("gt-7.9-ssor", "gt-7.9-ars"):
            continue
        base = Path(row["path"]).name
        if row["label"] == "gt-7.9-ssor":
            ssor_name = base
        for rel, rec in (inv["frozen_files"].get(row["label"]) or {}).items():
            by_key[f"{base}/{rel}"] = rec["sha256"]
    bare_alias = {key.split("/", 1)[1]: key for key in by_key
                  if ssor_name and key.startswith(f"{ssor_name}/"
                                                  "ramp_summary_excel/")}
    bindings = fs.get("archive_bindings") or ()
    if not bindings:
        fail("the manifest records no archive bindings")
        return
    covered = set()
    for b in bindings:
        zp = Path(b["archive"])
        if not zp.is_file():
            fail(f"archive MISSING: {zp}")
            continue
        if file_sha256(zp) != b["sha256"]:
            fail(f"archive changed: {zp}")
            continue
        if b["mismatched"]:
            fail(f"the manifest itself records archive mismatches for "
                 f"{zp.name}")
            continue
        matched = 0
        with zipfile.ZipFile(zp) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                key = archive_member_key(info.filename)
                key = bare_alias.get(key, key)
                want = by_key.get(key)
                if want is None:
                    continue
                h = hashlib.sha256()
                with zf.open(info) as fh:
                    for block in iter(lambda: fh.read(CHUNK), b""):
                        h.update(block)
                if h.hexdigest().upper() == want:
                    matched += 1
                    covered.add(key)
                else:
                    fail(f"{zp.name}: member no longer matches — {key}")
        print(f"  ok  {zp.name:<34} {matched:>6} member(s) re-matched")
    outside = sorted(k for k in by_key if k not in covered)
    if outside:
        fail(f"{len(outside)} ground-truth file(s) outside every archive, "
             f"e.g. {outside[:3]}")


# --------------------------------------------------------------------------- #
# --self-test: bounded NEGATIVE checks
# --------------------------------------------------------------------------- #
def self_test():
    """Prove the fail-closed behavior with fabricated fixtures — no real
    corpus is read or touched. Each case removes or corrupts exactly one
    declared item and requires the corresponding check to record a failure;
    a clean fixture must verify with none. Exits nonzero if ANY negative case
    passes silently."""
    import tempfile

    problems = []

    def expect(name, fn, wants_failure, needle=""):
        failures = []
        fn(failures.append)
        ok = bool(failures) == wants_failure and \
            (not needle or any(needle in f for f in failures))
        print(f"  [{'OK ' if ok else 'BAD'}] {name}"
              + (f"  ({failures[0][:70]})" if failures else ""))
        if not ok:
            problems.append(name)

    with tempfile.TemporaryDirectory(prefix="rb4_selftest_") as td:
        td = Path(td)
        root = td / "root"
        root.mkdir()
        (root / "a.bin").write_bytes(b"alpha")
        a_sha = file_sha256(root / "a.bin")
        rec = {"a.bin": {"bytes": 5, "sha256": a_sha}}

        print("negative checks — rehash_block")
        expect("clean root verifies with zero failures",
               lambda f: rehash_block("t", root, rec, f), False)
        expect("a MISSING declared root fails",
               lambda f: rehash_block("t", td / "absent", rec, f),
               True, "MISSING")
        expect("a missing declared file fails",
               lambda f: rehash_block("t", root,
                                      {**rec, "gone.bin": rec["a.bin"]}, f),
               True, "missing gone.bin")
        (root / "b.bin").write_bytes(b"beta")
        expect("changed bytes fail",
               lambda f: rehash_block(
                   "t", root, {"b.bin": {"bytes": 4,
                                         "sha256": "0" * 64}}, f),
               True, "content changed")
        expect("a replica that does not equal its frozen source fails",
               lambda f: rehash_block("t", root, rec, f,
                                      sources={"a.bin": "0" * 64}),
               True, "frozen source")

        print("negative checks — detached inventory binding")
        inv_path = td / "inv.json"
        inv_path.write_text(json.dumps({"frozen_files": {}}),
                            encoding="utf-8")
        good_inv = {"inventory": {"path": str(inv_path),
                                  "sha256": file_sha256(inv_path),
                                  "bytes": inv_path.stat().st_size}}
        expect("a clean inventory loads with zero failures",
               lambda f: (load_inventory(good_inv, f), None)[1] or None, False)
        inv_path.write_text(json.dumps({"frozen_files": {"x": {}}}),
                            encoding="utf-8")
        expect("a TAMPERED inventory fails and is not trusted",
               lambda f: (load_inventory(good_inv, f), None)[1] or None,
               True, "recorded sha256")
        expect("a MISSING inventory fails",
               lambda f: (load_inventory(
                   {"inventory": {"path": str(td / "gone.json"),
                                  "sha256": "0" * 64}}, f), None)[1] or None,
               True, "MISSING")

        print("negative checks — the manifest's own problem list")
        expect("a manifest with a non-empty problem list fails",
               lambda f: check_manifest_problems(
                   {"problems": ["the base tree is MISSING"]}, f),
               True, "records 1 build problem")
        expect("a manifest with NO problem list fails",
               lambda f: check_manifest_problems({}, f), True, "absent list")
        expect("an empty problem list passes",
               lambda f: check_manifest_problems({"problems": []}, f), False)

        print("negative checks — empty declarations")
        expect("an EMPTY declared file set fails",
               lambda f: rehash_block("t", root, {}, f), True, "EMPTY file set")
        expect("an EMPTY declared root list fails",
               lambda f: declared_roots("frozen_sources", [], f),
               True, "NO root")

        print("negative checks — exact head + self-stamps "
              "(driving check_exact_head itself)")
        head = "a" * 40

        def exact_manifest(entries, all_same=True):
            return {"acceptance_head": {"commit": head},
                    "results": {"entries": entries,
                                "all_claimed_same_head": all_same,
                                "off_head": [], "unstamped": []}}
        expect("a wrong-head and an unstamped claimed entry both fail",
               lambda f: check_exact_head(exact_manifest(
                   [{"path": "p1", "class": "acceptance", "role": "generate",
                     "runtime_head_commit": "b" * 40,
                     "self_stamp": {"tree_commit": "b" * 40,
                                    "tree_runtime_dirty": False}},
                    {"path": "p2", "class": "acceptance", "role": "counts"}],
                   all_same=False), None, f), True)
        expect("a DIRTY self-stamp fails even on the right head",
               lambda f: check_exact_head(exact_manifest(
                   [{"path": "p3", "class": "acceptance", "role": "validate",
                     "runtime_head_commit": head,
                     "self_stamp": {"tree_commit": head,
                                    "tree_runtime_dirty": True}}]), None, f),
               True, "CLEAN runtime")
        expect("a manifest with NO claimed entry fails",
               lambda f: check_exact_head(exact_manifest([]), None, f),
               True, "claims NO acceptance result")
        expect("a clean stamped entry passes",
               lambda f: check_exact_head(exact_manifest(
                   [{"path": "p4", "class": "acceptance", "role": "excel",
                     "runtime_head_commit": head,
                     "self_stamp": {"tree_commit": head,
                                    "tree_runtime_dirty": False}}]), None, f),
               False)

        print("the base side's OWN-stamp spellings (driving base_own_stamp)")
        expect("a single-tree base result's `tree_commit` is read",
               lambda f: (None if base_own_stamp({"tree_commit": "d" * 40})
                          == "d" * 40 else f("tree_commit not read")), False)
        expect("checks-at-base's `base_tree_commit` is read, NOT its "
               "`head_tree_commit`",
               lambda f: (None if base_own_stamp(
                   {"base_tree_commit": "d" * 40,
                    "head_tree_commit": "e" * 40}) == "d" * 40
                   else f("wrong side read")), False)
        expect("a body naming ONLY the head names no base commit of its own "
               "(no fallback to the head field)",
               lambda f: (None if base_own_stamp(
                   {"head_tree_commit": "e" * 40}) is None
                   else f("fell back to the HEAD's own field")), False)

        print("negative checks — the base side's binding "
              "(driving check_base_binding itself)")
        base = "d" * 40
        export = str(td / "base-tree")

        def base_manifest(stamp, commit=base, export_path=export,
                          head_tree=str(td / "head-tree")):
            return {"acceptance_head": {"commit": head},
                    "runtime": {"head": {"tree": head_tree}},
                    "base_tree": {"commit": commit,
                                  "export_path": export_path},
                    "results": {"entries": [
                        {"path": "counts-base.json",
                         "class": BASE_SIGNATURE_CLASS, "role": "counts",
                         "base_commit": commit, "base_stamp": stamp}]}}
        expect("a base result with tree_commit: null fails",
               lambda f: check_base_binding(base_manifest(
                   {"tree_commit": None, "tree": export}), f),
               True, "names NO runtime commit")
        expect("a base result with NO stamp at all fails",
               lambda f: check_base_binding(
                   {"acceptance_head": {"commit": head},
                    "runtime": {"head": {"tree": str(td / "head-tree")}},
                    "base_tree": {"commit": base, "export_path": export},
                    "results": {"entries": [
                        {"path": "counts-base.json",
                         "class": BASE_SIGNATURE_CLASS, "role": "counts"}]}},
                   f),
               True, "names NO runtime commit")
        expect("a base result stamped with the HEAD fails",
               lambda f: check_base_binding(base_manifest(
                   {"tree_commit": head, "tree": export}), f),
               True, "ACCEPTANCE HEAD")
        expect("a base commit equal to the head fails",
               lambda f: check_base_binding(base_manifest(
                   {"tree_commit": head, "tree": export}, commit=head), f),
               True, "IS the acceptance head")
        expect("a base export path equal to the head tree fails",
               lambda f: check_base_binding(base_manifest(
                   {"tree_commit": base, "tree": export},
                   head_tree=export), f),
               True, "IS the head tree")
        expect("a base result that ran in another tree fails",
               lambda f: check_base_binding(base_manifest(
                   {"tree_commit": base, "tree": str(td / "elsewhere")}), f),
               True, "not the recorded base export")
        expect("a manifest with NO base-signature result fails",
               lambda f: check_base_binding(
                   {"acceptance_head": {"commit": head},
                    "runtime": {"head": {"tree": str(td / "head-tree")}},
                    "base_tree": {"commit": base, "export_path": export},
                    "results": {"entries": []}}, f),
               True, "no base-signature result")
        expect("an explicitly bound base side passes",
               lambda f: check_base_binding(base_manifest(
                   {"tree_commit": base, "tree": export,
                    "tree_runtime_dirty": False}), f),
               False)

        print("negative checks — witness binding")
        wdir = td / "repo" / "w"
        wdir.mkdir(parents=True)
        wfile = wdir / "wit.json"
        wfile.write_text(json.dumps({
            "bound_to_acceptance_head": "c" * 40,
            "produced_by": {"script": "s.py", "script_sha256": "0" * 64}}),
            encoding="utf-8")
        mani = {"acceptance_head": {"commit": head},
                "harness": {"files": {"s.py": {"sha256": "1" * 64}}},
                "results": {"entries": [
                    {"path": str(wfile), "repo_path": "w/wit.json",
                     "sha256": file_sha256(wfile),
                     "class": "acceptance", "role": "committed-witness",
                     "runtime_head_commit": head}]}}
        expect("a witness bound to the WRONG head fails",
               lambda f: check_witnesses(mani, td / "repo", f),
               True, "bound to")
        wfile.write_text(json.dumps({
            "bound_to_acceptance_head": head,
            "produced_by": {"script": "s.py", "script_sha256": "0" * 64}}),
            encoding="utf-8")
        mani["results"]["entries"][0]["sha256"] = file_sha256(wfile)
        expect("a witness whose producer is unbound fails",
               lambda f: check_witnesses(mani, td / "repo", f),
               True, "harness block")

    print(f"\nSELF-TEST {'FAILED' if problems else 'PASSED'} — "
          f"{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    if args[0] == "--self-test":
        self_test()
        return
    manifest = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    tree = Path(".")
    corpus = zips = False
    i = 1
    while i < len(args):
        if args[i] == "--tree":
            tree = Path(args[i + 1]); i += 2
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

    check_manifest_problems(manifest, fail)
    check_runtime(manifest, tree, fail)
    check_lineage(manifest, tree, fail)
    check_exact_head(manifest, tree, fail)
    check_base_tree(manifest, tree, fail)
    check_base_binding(manifest, fail)
    check_witnesses(manifest, tree, fail)
    if corpus:
        check_corpus(manifest, tree, fail)
    else:
        print("\nCORPUS — not requested (pass --corpus to re-hash it)")
    if zips:
        check_zips(manifest, fail)
    elif corpus:
        print("\nZIPS — not requested (pass --zips to re-match the frozen "
              "archives)")

    print(f"\n{'FAILED' if failures else 'VERIFIED'} — "
          f"{len(failures)} problem(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
