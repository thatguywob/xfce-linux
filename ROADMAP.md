# XFCE Linux Roadmap

**Last updated**: 2026-10-31 | **Status**: Alpha — first release blocked

Part of the [TunaOS](https://tunaos.org) ecosystem. XFCE Linux is the
lightweight XFCE Wayland OCI image, built from source with BuildStream.

## Current strategic focus

The near-term goal is one reproducible, installable Beta release. Release
readiness is measured by a promoted outcome, not by the presence of workflows
or the closure of implementation issues.

As of 2026-10-31, the repository has no GitHub Release or Git tag. Since the
previous update, these changes landed: the runner disk exhaustion fix (#161),
key-based Cosign image signing (#164), single-layer OCI composition without the
GNOME stack (#168), XFCE built from upstream release tags (#167), and
publication, signing, and scanning on scheduled builds (#241). Scheduled
multi-runner builds now pass and push the image to GHCR, but the downstream
live-ISO runs fail at ISO signing and the scheduled plain install check fails.
The project therefore remains in Alpha even though the stable-promotion
machinery exists.

## Alpha → Beta release gate

All evidence below must refer to the same candidate commit. The release tracker
stays open until every row is evidenced.

| Outcome | Exit evidence | Status (2026-10-31) |
| --- | --- | --- |
| Reproducible OCI image | A scheduled multi-runner build publishes an image and records its immutable digest | In progress — scheduled builds passed on 2026-10-29, 2026-10-30, and 2026-10-31 and pushed to GHCR; the latest image went out unsigned, and the release tracker has no candidate digest |
| Matching live media | ISO, checksum, signature, and certificate are published for the candidate | Blocked — live-ISO runs build the ISO but fail at `Sign ISO (cosign keyless)` |
| Install validation | Plain and LUKS install E2E checks pass against the candidate | Blocked — latest scheduled LUKS check passed (2026-10-26); latest scheduled plain check failed (2026-10-27, #135) |
| Stable promotion | `stable` resolves to the candidate digest and the promotion workflow verifies the image and ISO objects | Blocked on build and install gates |
| Discoverable release | A GitHub Release records the digest, signed artifact URLs, known limitations, and upgrade path | Not started — no releases or tags |
| User-path validation | The public install guide is followed successfully against the promoted candidate | Not started |

The first five rows are release blockers. User-path validation may be completed
with a release candidate, but must be recorded before Beta is announced.

## Operating cadence

- Review the release gate weekly while any blocker is red.
- Link each row to a durable workflow run, digest, artifact, or documentation
  check in the release tracker.
- Reopen the release tracker when evidence regresses before promotion.
- Do not count workflow implementation or a single isolated green job as a
  completed release outcome.

## After the first Beta

1. Publish a documented release cadence and support window.
2. Track XFCE and base-runtime currency with upgrade-test evidence.
3. Validate the lightweight positioning with boot-time, memory, and image-size
   measurements against at least one mainstream TunaOS desktop.
4. Evaluate HWE and ARM64 only after the Beta release gate is repeatable; each
   additional hardware target must include an owner and ongoing CI capacity.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
