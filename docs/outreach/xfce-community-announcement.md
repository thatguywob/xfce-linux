# XFCE community announcement kit

Tracking: [#217](https://github.com/tuna-os/xfce-linux/issues/217).
Status: drafts for maintainer review; no external announcement has been posted.

## Announcement / editorial pitch

Subject: Introducing XFCE Linux: an independent lightweight XFCE Wayland bootc desktop project

Hello XFCE community,

We would like to introduce [XFCE Linux](https://github.com/tuna-os/xfce-linux), an
independent community project in the [TunaOS](https://tunaos.org) ecosystem building
a lightweight, Wayland-native XFCE desktop from source using BuildStream 2, targeting
transactional, bootable OCI container images managed with `bootc`.

XFCE Linux is an independent project and makes no claim of official endorsement by
or formal affiliation with the XFCE core development team or the XFCE project.

### Project Focus

Our goal is bringing the lightweight, responsive experience of XFCE into the emerging
space of immutable and transactional operating systems:

- **Wayland-native desktop**: Incorporating the `xfwl4` compositor alongside core XFCE
  components (`xfce4-panel`, `xfdesktop`, `thunar`, `xfce4-terminal`, and supporting
  panel plugins).
- **Source-based composition**: Built with [BuildStream 2](https://buildstream.build/)
  on top of freedesktop-sdk and GNOME OS base elements (`gnome-build-meta.bst:oci/gnomeos/stack.bst`),
  providing transparent, hermetic, and reproducible builds.
- **Transactional updates via bootc**: Packaging the operating system as an OCI container
  image updated transactionally with `bootc switch` and `bootc upgrade`, ensuring atomic
  deployments with instant rollbacks and no half-upgraded package states.
- **Sustainability and resource-constrained systems**: Offering a modern Wayland desktop
  stack for older PCs, laptops, and memory-constrained systems without the software rot
  and maintenance overhead common to long-lived traditional installations.

The repository brings together element definitions, OCI image composition layers, live
ISO generation recipes, and automated end-to-end installation tests in one place.

### Current Maturity and Status

In accordance with our [roadmap](https://github.com/tuna-os/xfce-linux/blob/main/ROADMAP.md),
XFCE Linux is currently in **Alpha** status (first release blocked).

While multi-runner build orchestration, live ISO recipes, and plain/LUKS installation
test harnesses are in place, scheduled candidate builds and ISO generation remain under
active stabilization. Architectural transitions are also in progress—specifically
migrating package sources to upstream release tags ([#167](https://github.com/tuna-os/xfce-linux/issues/167))
and streamlining the OCI layer stack ([#168](https://github.com/tuna-os/xfce-linux/issues/168)).
Furthermore, as documented in [`docs/signing.md`](https://github.com/tuna-os/xfce-linux/blob/main/docs/signing.md),
OCI image signing with Cosign keys is planned but not yet in effect.

Therefore, this introduction is an invitation for technical collaboration and early
feedback, rather than an announcement of a production-ready or general-availability release.

### Call for Collaboration

We welcome feedback and participation from XFCE maintainers, packagers, and immutable
desktop contributors:

1. **Wayland & Compositor Testing**: Evaluating `xfwl4` behavior, panel integration,
   and window management under Wayland.
2. **BuildStream Packaging**: Sharing packaging recipes and source definitions that may
   benefit the wider XFCE and freedesktop ecosystems.
3. **Resource Benchmarking**: Testing memory footprint, idle overhead, and boot responsiveness
   on older hardware configurations.

Please report project-specific issues and track technical progress on our
[issue tracker](https://github.com/tuna-os/xfce-linux/issues).

- **Repository**: https://github.com/tuna-os/xfce-linux
- **Architecture & Gotchas**: https://github.com/tuna-os/xfce-linux/blob/main/AGENTS.md
- **Contributing Guide**: https://github.com/tuna-os/xfce-linux/blob/main/CONTRIBUTING.md
- **Pipeline & Invariants**: https://github.com/tuna-os/xfce-linux/blob/main/docs/ci-and-iso-pipeline.md

Thank you to the XFCE maintainers and community for three decades of building an efficient,
reliable desktop environment.

---

## Short forum / social media cross-post

Title: XFCE Linux: exploring lightweight XFCE Wayland with BuildStream and bootc

XFCE Linux is an independent TunaOS community project building a lightweight XFCE
desktop on freedesktop-sdk using BuildStream 2, targeting transactional OCI/bootc system
images.

The project integrates the `xfwl4` Wayland compositor with XFCE core components
(`xfce4-panel`, `thunar`, `xfdesktop`), BuildStream build orchestration, and live ISO
tooling. It is independent of the upstream XFCE project and remains in Alpha status;
please check our roadmap release gates and current build status before testing.

We welcome feedback on `xfwl4` Wayland behavior, desktop smoke testing, and packaging
collaboration.

- Project overview and code: https://github.com/tuna-os/xfce-linux
- Release roadmap and gates: https://github.com/tuna-os/xfce-linux/blob/main/ROADMAP.md
- Discussion and issue reports: https://github.com/tuna-os/xfce-linux/issues

*(When cross-posting to forums or social channels, please link back to the canonical
announcement so discussion and feedback can be tracked.)*

---

## Content creator & sustainability pitch (e-waste repurposing)

Subject: Story pitch: Giving decade-old laptops a second life with XFCE Wayland and bootc

Hello,

The conversation around tech sustainability and circular computing frequently hits a
pain point: older laptops have capable hardware for everyday tasks, but software rot,
heavy modern desktop environments, and broken system updates eventually push them into
the recycling bin.

XFCE Linux is exploring a fresh technical angle on this problem: pairing the lightweight
efficiency of XFCE and modern Wayland display protocol with the transactional reliability
of `bootc` container-based OS updates.

### Key Talking Points

- **Zero "OS Rot" on Aging Hardware**: Traditional package managers can accumulate cruft
  or land in inconsistent states across multiple release cycles. With `bootc`, system
  updates are atomic image deployments: updates either succeed completely or roll back
  instantly to the previous known-working boot state.
- **Modern Display Protocol on Low Resources**: Running the lightweight `xfwl4` compositor
  provides modern Wayland session handling without the heavy CPU and GPU memory footprint
  of larger desktop shells.
- **Reproducible, Open Composition**: Built transparently from source via BuildStream 2,
  avoiding proprietary blobs and keeping the base image lean.
- **Realistic Project Status**: The project is currently in Alpha as core CI pipelines
  and upstream source packaging are stabilized. We are actively seeking hardware testing
  insights and feedback from creators interested in open-source longevity and sustainability.

If you are planning coverage, testing, or video projects around lightweight Linux, hardware
repurposing, or the next generation of image-based operating systems, we would be happy
to share technical details, build configs, and early test images.

Project link: https://github.com/tuna-os/xfce-linux

---

## Evidence and publication checklist

A maintainer should review the draft copy, confirm current pipeline evidence, and act as
the public sender before publishing. Record the sender identity and publication URLs in
issue [#217](https://github.com/tuna-os/xfce-linux/issues/217). Issue #217 remains open
until external publication and cross-posting are completed.

### Pre-Publication Review

- [ ] **Roadmap Alignment**: Reconcile any claims with the Alpha release gate in
  `ROADMAP.md`. Do not claim verified Beta readiness, stable release promotion, or
  guaranteed ISO downloads until candidate build and install test runs are green.
- [ ] **Signature Clarifications**: Verify that copy accurately reflects `docs/signing.md`.
  OCI image signing is not yet active in CI; live ISO signing uses keyless cosign OIDC.
  Do not advertise verified OCI image signatures until Cosign key generation and policy
  configuration land.
- [ ] **Upstream Independence & Trademark**: Ensure all public copy clearly designates
  XFCE Linux as an independent community project. Comply with XFCE trademark guidelines
  and avoid any impression of official XFCE project governance or endorsement.
- [ ] **Architecture Accuracy**: Verify that package lists, compositor references (`xfwl4`),
  and base image descriptions match the current state in `elements/` and `AGENTS.md`.
  Note that ARM64/HWE support is slated for evaluation only after x86_64 Beta release gates
  are repeatable.

### Channel Selection & Posting

- [ ] **XFCE Development & Discussion**: Verify active posting etiquette for XFCE mailing
  lists (`xfce@xfce.org` / `xfce-dev@xfce.org` via [mail.xfce.org](https://mail.xfce.org/mailman/listinfo/)).
  Do not submit announcement copy as bug tickets on `gitlab.xfce.org`.
- [ ] **XFCE Forum**: Post to the appropriate category on [forum.xfce.org](https://forum.xfce.org/)
  (e.g., General Discussion or Announcements) in accordance with forum rules.
- [ ] **Fediverse / Social Media**: Post short copy on Mastodon targeting relevant tags
  (`#xfce`, `#bootc`, `#linux`, `#tunaos`) and mention `@xfce@floss.social` respectfully.
- [ ] **TunaOS Documentation**: Only link to `tunaos.org/docs/xfce-linux` once the
  external documentation page is active and verified; use repository links until then.
- [ ] **Record Publication**: Note live links, date of publication, and community feedback
  in issue [#217](https://github.com/tuna-os/xfce-linux/issues/217).
