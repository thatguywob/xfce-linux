# Install end-to-end tests

These tests boot the live ISO in QEMU, install onto a disposable virtual disk
with fisherman, reboot from that disk, and check the installed system reaches
a ready state using serial boot markers (and framebuffer heuristics for
LUKS). The LUKS scenario also enters the test passphrase at boot.
The assertions and orchestration live in `iso.justfile`, `scripts/`, and
`xfce-linux/src/luks-unlock.py`; this directory provides a common entry point.

Run on a Linux host with KVM, QEMU, OVMF, `just`, SSH/sshpass, Python 3 and
sudo. Build a debug ISO first (SSH is needed for the install):

```bash
just debug=1 iso-sd-boot xfce-linux
bash tests/e2e/run.sh plain
bash tests/e2e/run.sh luks
```

Run scenarios sequentially: the existing recipes share VM ports and sockets.
Each command returns nonzero if installation or boot verification fails.
The recipes create test disks under `/var/tmp` and serial logs and QEMU
monitor sockets under `/tmp`; inspect these when diagnosing a failure.
Use only disposable test artifacts: the recipes recreate their virtual disks.
The installed VM may remain running for inspection; stop it via its QEMU
monitor before another run (see the recipe's printed endpoints).

The runner accepts just variable overrides, target and installer channel:

```bash
bash tests/e2e/run.sh plain output_dir=/path/to/isos xfce-linux stable
```

It builds nothing and delegates to `just plain-test-qemu` or
`just luks-test-qemu`, the same recipes run by
`.github/workflows/test-plain-install.yml` and `test-luks-install.yml`.
Those workflows build their ISO and retain logs/screenshots as artifacts.
The PR gate in `test.yml` selects the affected scenarios; scheduled and manual
runs provide full coverage. Heavy image builds belong in CI.

For fast checks without a VM, run `bats tests/bats/*.bats` and
`python3 -m pytest tests/pytest/ -v` instead.
