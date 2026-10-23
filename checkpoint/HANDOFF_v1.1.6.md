# v1.1.6 continuation checkpoint

User authorized: audit all main-game vs UOP/USIP/UODP translations (not only BOOK), correct, release and update Nexus.

Reviewed source commit: b4c36e4d5c22f8445b30e38f9415487bd618555c
Reviewed tree: 0f2e7ec51e0db5a09d947e14e8a2144196364f13
Required base: 5509d07652100e0bfd3e364d184fa6673b0c0270
Bundle: checkpoint/oblivion-v1.1.6.bundle
Bundle SHA256: 839fca03d0f9f2dc10110ede2300687eb8a6fa4f1a3d5879039f87da4f72e5ec

Recover from repository root after checking out this checkpoint branch:
  git bundle verify checkpoint/oblivion-v1.1.6.bundle
  git fetch checkpoint/oblivion-v1.1.6.bundle HEAD
  git switch -c release/oblivion-v1.1.6 FETCH_HEAD
Verify exact reviewed commit and tree above. Do not mistake the checkpoint commit for the reviewed source commit.

Completed: 10,320 tracked fields audited, remaining visible fields inventoried; 133 untracked fields already match main, 82 patch-only/no-main fields retained, 5 race names kept English for voice paths. Source alignment covers dialogue, journals, names, descriptions, ranks, locations and books. All forwarding pins both English hashes and master owner, record type, FormID, EDID and occurrence. Exact unique text is explicitly mapped across reordered journal occurrences. 51 patch-specific mistranslations corrected (2 overlap base alignment), rather than reverting meaningful patch changes. Actual published binaries: UOP 508 changes, USIP 92, UODP 16, total 616. Main Darkest Darkness '마봄비의 4월' corrected to '접촉 마비 능력'; reviewed proper names forwarded. Frozen installer now includes fur correction CSV.

Validated: 108 tests pass; record/script signatures and every unselected subrecord preserved; 8 of 13 shipped ESPs byte-identical; normal builder source-field replay agrees with refresh output on all 9,719 mapped fields. No real-game verification was performed. No user game installation was modified.

Source files, manifests, full compressed audit, manual-fix audit, summary, build parity, release notes, packaging script, installer spec and release/Nexus workflow are all in the reviewed commit.

NOT completed: reviewed source is NOT on main; no v1.1.6 GitHub release; no Nexus upload. Native git push failed due unavailable HTTPS credentials. GitHub connector remains authenticated with write/admin repository permission. Large canonical blob fetch through connector returned Transport closed. This bundle checkpoint preserves the entire exact tested source independently of scratch.

Next: retrieve/import bundle; inspect final diff; publish reviewed source to main without overwriting concurrent work; run .github/workflows/release-v1.1.6.yml; fix build failures if any; verify release assets and all four Nexus jobs. Workflow builds Windows installer, refreshes three unofficial packages from hash-pinned v1.1.5 public assets, verifies replay parity, creates v1.1.6 release, uploads installer/UOP/USIP/UODP using existing NEXUSMODS_API_KEY secret and pinned upload action. No browser sign-in is needed if workflow works.

Potential deployment concern: adding or changing workflows needs the appropriate GitHub credential capability. A source push performed with GITHUB_TOKEN normally does not trigger another on:push run. Explicit workflow dispatch or a subsequent authenticated connector commit touching release_notes_v1.1.6.md may be needed. Do not call a queued workflow a completed release/upload.

Current scratch repository: /workspace/scratch/829a3d0eacdf/Oblivion-KR-Translation
Scratch reviewed bundle: /tmp/oblivion-v116.bundle
Scratch packages: /tmp/full-release-v3 (older /tmp/full-release-v2 and repo/dist are superseded BOOK-only/earlier drafts; DO NOT publish those)
Scratch original public package fixtures: /tmp/uop-baseline.zip, /tmp/usip-baseline.zip, /tmp/uodp-baseline.zip; extracted ESPs /tmp/all-baseline.
Scratch /tmp/full-release-v3 packages were built before final README expansion; their ESPs are final but CI should regenerate ZIPs from committed docs.

Report glyph/tofu and unspecified Ayleid puzzle-message complaints remain unlocalized to exact source records; do not claim they are fixed. Main v1.1.5 obCJK runtime DLL was not modified. User asked to see Darkest Darkness example; actual old/new snippets already supplied.
