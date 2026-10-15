# XFCE Linux — Documentation Index

This directory holds two kinds of documentation: infrastructure docs (image
and artifact signatures, the CI/ISO pipeline, ADRs) and archived session
reports. For the project overview, build and run instructions, and current
status, start with the top-level docs instead:

- **[../README.md](../README.md)** — what this image is, how to pull or
  build it, the stable release channel, and signature verification.
- **[../AGENTS.md](../AGENTS.md)** — an architecture summary, `just`
  commands, and hard-won gotchas for anyone, human or agent, who works on
  this repo.
- **[`../CONTRIBUTING.md`](../CONTRIBUTING.md)** — the contributor workflow
  and how to set up a development environment.

## In this directory

- **[ci-and-iso-pipeline.md](ci-and-iso-pipeline.md)** — the full CI to
  image to ISO chain, with a log of past problems and fixes. Update this
  file when you fix a CI or ISO bug (see AGENTS.md's CI gate rules).
- **[`signing.md`](signing.md)** — the cosign setup for image signatures
  (not yet in effect).
- **[adr/](adr/)** — architecture decision records (for example,
  [0001-wayland-greeter.md](adr/0001-wayland-greeter.md)).
- **[technical/](technical/)** and **[reference/](reference/)** — dated
  session reports from early development (May to August 2026), kept for
  history. Each file carries an `ste-disable-file` marker and describes a
  point-in-time snapshot, not the current state. Do not treat metrics,
  "Known Issues," or completion percentages in these files as current. The
  top-level README and AGENTS.md reflect what ships today.
