# ISO/live/e2e recipes live in iso.justfile (kept separate for readability)
import "iso.justfile"
import "just/buildstream.just"
import "just/disk-image.just"

# List available commands
[group('info')]
default:
    @just --list

# ── Configuration ─────────────────────────────────────────────────────
export image_name := env("BUILD_IMAGE_NAME", "xfce-linux")
export image_tag := env("BUILD_IMAGE_TAG", "latest")
export base_dir := env("BUILD_BASE_DIR", ".")
export filesystem := env("BUILD_FILESYSTEM", "ext4")

# Same bst2 container image CI uses -- pinned by SHA for reproducibility
export bst2_image := env("BST2_IMAGE", "registry.gitlab.com/freedesktop-sdk/infrastructure/freedesktop-sdk-docker-images/bst2:latest")

# VM settings
export vm_ram := env("VM_RAM", "8192")
export vm_cpus := env("VM_CPUS", "4")

# OCI metadata (dynamic labels)
export OCI_IMAGE_CREATED := env("OCI_IMAGE_CREATED", "")
export OCI_IMAGE_REVISION := env("OCI_IMAGE_REVISION", "")
export OCI_IMAGE_VERSION := env("OCI_IMAGE_VERSION", "latest")

# ── Boot VM ──────────────────────────────────────────────────────────
# Boot the raw disk image.
# If qemu-system-x86_64 is installed, runs natively (UEFI/OVMF).
# Otherwise, falls back to running via docker.io/qemux/qemu-docker.
[group('test')]
boot-vm $base_dir=base_dir:
    #!/usr/bin/env bash
    set -euo pipefail

    # Resolve absolute path for Docker volume mount
    DISK=$(realpath "{{base_dir}}/bootable.raw")
    if [ ! -e "$DISK" ]; then
        echo "ERROR: ${DISK} not found. Run 'just generate-bootable-image' first." >&2
        exit 1
    fi

    # Check for native QEMU
    if command -v qemu-system-x86_64 &>/dev/null; then
        echo "==> Using native qemu-system-x86_64..."

        # Auto-detect OVMF firmware paths
        OVMF_CODE=""
        for candidate in \
            /usr/share/edk2/ovmf/OVMF_CODE.fd \
            /usr/share/OVMF/OVMF_CODE.fd \
            /usr/share/OVMF/OVMF_CODE_4M.fd \
            /usr/share/edk2/x64/OVMF_CODE.4m.fd \
            /usr/share/qemu/OVMF_CODE.fd; do
            if [ -f "$candidate" ]; then
                OVMF_CODE="$candidate"
                break
            fi
        done
        if [ -z "$OVMF_CODE" ]; then
            echo "ERROR: OVMF firmware not found. Install edk2-ovmf (Fedora) or ovmf (Debian/Ubuntu)." >&2
            exit 1
        fi

        # OVMF_VARS must be writable -- use a local copy
        OVMF_VARS="{{base_dir}}/.ovmf-vars.fd"
        if [ ! -e "$OVMF_VARS" ]; then
            OVMF_VARS_SRC=""
            for candidate in \
                /usr/share/edk2/ovmf/OVMF_VARS.fd \
                /usr/share/OVMF/OVMF_VARS.fd \
                /usr/share/OVMF/OVMF_VARS_4M.fd \
                /usr/share/edk2/x64/OVMF_VARS.4m.fd \
                /usr/share/qemu/OVMF_VARS.fd; do
                if [ -f "$candidate" ]; then
                    OVMF_VARS_SRC="$candidate"
                    break
                fi
            done
            if [ -z "$OVMF_VARS_SRC" ]; then
                echo "ERROR: OVMF_VARS not found alongside OVMF_CODE." >&2
                exit 1
            fi
            cp "$OVMF_VARS_SRC" "$OVMF_VARS"
        fi

        echo "==> Booting ${DISK} in QEMU (UEFI, KVM)..."
        echo "    Firmware: ${OVMF_CODE}"
        echo "    RAM: {{vm_ram}}M, CPUs: {{vm_cpus}}"
        echo "    Serial debug shell on ttyS1 available via QEMU monitor"
        echo ""

        qemu-system-x86_64 \
            -enable-kvm \
            -m "{{vm_ram}}" \
            -cpu host \
            -smp "{{vm_cpus}}" \
            -drive file="${DISK}",format=raw,if=virtio \
            -drive if=pflash,format=raw,readonly=on,file="${OVMF_CODE}" \
            -drive if=pflash,format=raw,file="${OVMF_VARS}" \
            -device virtio-gpu-pci \
            -display egl-headless,rendernode=/dev/dri/renderD128 \
            -vnc 127.0.0.1:1 \
            -device virtio-keyboard \
            -device virtio-mouse \
            -device virtio-net-pci,netdev=net0 \
            -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2223-:22 \
            -serial telnet:127.0.0.1:4445,server,nowait \
            -serial telnet:127.0.0.1:4447,server,nowait \
            -monitor unix:./qemu-monitor.sock,server,nowait \
            -daemonize -pidfile /tmp/xfce-linux-vm.pid






    else
        echo "==> qemu-system-x86_64 not found, falling back to docker.io/qemux/qemu-docker..."

        # Check for qcow2 image, prefer it if exists
        BOOT_MOUNT="/boot.img"
        if [ -e "{{base_dir}}/bootable.qcow2" ]; then
            DISK=$(realpath "{{base_dir}}/bootable.qcow2")
            BOOT_MOUNT="/boot.qcow2"
        fi

        # Determine which port to use
        port=8006
        while grep -q :${port} <<< $(ss -tunalp); do
            port=$(( port + 1 ))
        done
        echo "==> Web/VNC accessible at http://localhost:${port}"

        # Try to open browser
        xdg-open "http://localhost:${port}" &>/dev/null || true

        # Run via podman
        podman run \
            --rm --privileged \
            --device /dev/kvm \
            --pull=always \
            --publish "127.0.0.1:${port}:8006" \
            --publish "127.0.0.1:2222:22" \
            --env "USER_PORTS=22" \
            --env "NETWORK=user" \
            --env "CPU_CORES={{vm_cpus}}" \
            --env "RAM_SIZE={{vm_ram}}" \
            --env "TPM=y" \
            --env "BOOT_MODE=${BOOT_MODE:-uefi}" \
            --env "ARGUMENTS=-snapshot" \
            --volume "${DISK}:${BOOT_MOUNT}" \
            ghcr.io/qemus/qemu:latest
    fi

# ── Boot in libvirt ──────────────────────────────────────────────────
[group('test')]
boot-libvirt name="xfce-linux" ram="8192" cpus="4":
    #!/usr/bin/env bash
    set -euo pipefail

    DISK=$(realpath "{{base_dir}}/bootable.qcow2")
    FORMAT="qcow2"
    if [ ! -e "$DISK" ]; then
        DISK=$(realpath "{{base_dir}}/bootable.raw")
        FORMAT="raw"
    fi

    if [ ! -e "$DISK" ]; then
        echo "Error: Disk image not found. Run 'just generate-bootable-image' first."
        exit 1
    fi

    # Destroy and undefine existing VM if it exists
    sudo virsh destroy "{{name}}" 2>/dev/null || true
    sudo virsh undefine "{{name}}" --nvram 2>/dev/null || true

    NVRAM_DST="/var/lib/libvirt/qemu/nvram/{{name}}_VARS.fd"
    sudo cp /usr/share/edk2/ovmf/OVMF_VARS.fd "${NVRAM_DST}"

    echo "==> Creating libvirt domain '{{name}}' (format: ${FORMAT})..."
    TMPL="{{justfile_directory()}}/files/vm/domain-template.xml"
    XML=$(mktemp --suffix=.xml)
    sed \
        -e "s|VM_NAME|{{name}}|g" \
        -e "s|VM_RAM|{{ram}}|g" \
        -e "s|VM_CPUS|{{cpus}}|g" \
        -e "s|VM_FORMAT|${FORMAT}|g" \
        -e "s|VM_DISK|${DISK}|g" \
        -e "s|NVRAM_DST|${NVRAM_DST}|g" \
        "${TMPL}" > "${XML}"
    sudo virsh define "${XML}"
    rm -f "${XML}"
    sudo virsh start "{{name}}"

    echo "==> VM '{{name}}' started (qemu:///system)."
    echo "==> Connect with: virt-viewer {{name}}"
    echo "==> or open Virtual Machine Manager (virt-manager)."
    echo "==> VNC: $(sudo virsh vncdisplay {{name}} 2>/dev/null || echo 'check virt-manager')"

# ── Get VM IP address ─────────────────────────────────────────────────
[group('test')]
vm-ip name="xfce-linux":
    sudo virsh -c qemu:///system domifaddr "{{name}}" \
        | awk '/ipv4/{gsub(/\/[0-9]+/,"",$4); print $4; exit}'

# ── SSH into the VM ───────────────────────────────────────────────────
[group('test')]
ssh name="xfce-linux":
    #!/usr/bin/env bash
    set -euo pipefail
    IP=$(just vm-ip "{{name}}")
    if [ -z "$IP" ]; then
        echo "ERROR: could not get IP for '{{name}}'. Is the VM running?" >&2
        exit 1
    fi
    echo "==> SSH to root@${IP}"
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "root@${IP}"

# ── Collect crash logs from VM console ───────────────────────────────
[group('test')]
logs name="xfce-linux":
    /home/linuxbrew/.linuxbrew/bin/python3 {{justfile_directory()}}/scripts/vm-logs "{{name}}"

# ── Boot VM and collect logs in one shot ─────────────────────────────
[group('test')]
test name="xfce-linux":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "==> Starting VM '{{name}}'..."
    sudo virsh -c qemu:///system start "{{name}}" 2>/dev/null || true
    echo "==> Waiting 45s for boot..."
    sleep 45
    just logs "{{name}}"

# ── Show me the future ────────────────────────────────────────────────
# The full end-to-end: build the OCI image, install it to a bootable
# disk, and launch it in a QEMU VM. One command to rule them all.
[group('test')]
show-me-the-future:
    #!/usr/bin/env bash
    set -euo pipefail

    # ── Helpers ───────────────────────────────────────────
    HAS_GUM=false
    command -v gum &>/dev/null && [[ -t 1 ]] && HAS_GUM=true

    OVERALL_START=$SECONDS

    format_time() {
        local secs=$1
        if (( secs >= 3600 )); then
            printf '%dh %02dm %02ds' $((secs / 3600)) $(((secs % 3600) / 60)) $((secs % 60))
        elif (( secs >= 60 )); then
            printf '%dm %02ds' $((secs / 60)) $((secs % 60))
        else
            printf '%ds' "$secs"
        fi
    }

    step_start() {
        local name=$1
        if $HAS_GUM; then
            gum style --foreground 212 --bold "◔ ${name}..."
        else
            echo "==> ${name}..."
        fi
    }

    step_done() {
        local name=$1 elapsed=$2
        if $HAS_GUM; then
            gum style --foreground 46 "● ${name} ($(format_time "$elapsed"))"
        else
            echo "==> ${name} done ($(format_time "$elapsed"))"
        fi
    }

    step_failed() {
        local name=$1 elapsed=$2
        if $HAS_GUM; then
            gum style --foreground 196 "◍ ${name} FAILED ($(format_time "$elapsed"))"
        else
            echo "==> ${name} FAILED ($(format_time "$elapsed"))"
        fi
    }

    run_step() {
        local name=$1; shift
        step_start "$name"
        local start=$SECONDS
        if "$@"; then
            step_done "$name" $((SECONDS - start))
        else
            step_failed "$name" $((SECONDS - start))
            echo ""
            if $HAS_GUM; then
                gum style --foreground 196 --border rounded --align center --padding "1 2" \
                    'BUILD FAILED' \
                    "Failed: ${name}" \
                    "Total elapsed: $(format_time $((SECONDS - OVERALL_START)))"
            else
                echo "BUILD FAILED: ${name}"
                echo "Total elapsed: $(format_time $((SECONDS - OVERALL_START)))"
            fi
            exit 1
        fi
    }

    # ── Banner ────────────────────────────────────────────
    if $HAS_GUM; then
        TERM_WIDTH=$(tput cols 2>/dev/null || echo 80)
        BANNER_WIDTH=$((TERM_WIDTH > 62 ? 60 : TERM_WIDTH - 4))
        gum style \
            --foreground 212 \
            --border-foreground 212 \
            --border double \
            --align center \
            --width $BANNER_WIDTH \
            --margin "1 2" \
            --padding "1 4" \
            'SHOW ME THE FUTURE' \
            'Building XFCE Linux from source and booting it in a VM'
    else
        echo ""
        echo "=== SHOW ME THE FUTURE ==="
        echo "Building XFCE Linux from source and booting it in a VM"
    fi
    echo ""

    # ── Steps ─────────────────────────────────────────────
    run_step "Build OCI image" just build
    echo ""
    run_step "Bootable disk" just generate-bootable-image
    echo ""

    # Step 3: VM is interactive -- just announce it
    step_start "Launch VM"
    just boot-vm
    echo ""

    # ── Completion ────────────────────────────────────────
    if $HAS_GUM; then
        gum style --foreground 46 "● Launch VM"
        echo ""
        gum style \
            --foreground 46 \
            --border-foreground 46 \
            --border rounded \
            --align center \
            --width 42 \
            --padding "1 2" \
            'ALL STEPS COMPLETE' \
            "Total: $(format_time $((SECONDS - OVERALL_START)))"
    else
        echo "==> All steps complete. Total: $(format_time $((SECONDS - OVERALL_START)))"
    fi

# ── Chunkah ──────────────────────────────────────────────────────────
chunkify image_ref:
    #!/usr/bin/env bash
    set -euo pipefail

    SUDO_CMD=""
    if [ "$(id -u)" -ne 0 ]; then
        SUDO_CMD="sudo"
    fi

    echo "==> Chunkifying {{image_ref}}..."

    CONFIG=$($SUDO_CMD podman inspect "{{image_ref}}")

    FAKECAP_RESTORE="{{justfile_directory()}}/files/fakecap/fakecap-restore"
    if [ ! -x "$FAKECAP_RESTORE" ]; then
        echo "==> Compiling fakecap-restore..."
        gcc -O2 -o "$FAKECAP_RESTORE" "{{justfile_directory()}}/files/fakecap/fakecap-restore.c"
    fi

    if [ "${CHUNKIFY_REUSE_FILEMAP:-0}" = "1" ]; then
        # build_final generates these while the BuildStream CAS still exists,
        # then deletes the CAS to leave enough room for the OCI export (#159).
        # Fail explicitly instead of applying an empty or stale manifest.
        for manifest in files/filemap.json files/fakecap-manifest.tsv; do
            if [ ! -s "$manifest" ]; then
                echo "ERROR: CHUNKIFY_REUSE_FILEMAP=1 but $manifest is missing or empty" >&2
                exit 1
            fi
        done
        echo "==> Reusing the existing component filemap..."
    else
        echo "==> Generating component filemap..."
        python3 scripts/gen-filemap.py
    fi

    LOWER=$($SUDO_CMD podman image mount "{{image_ref}}")

    cleanup() {
        $SUDO_CMD umount "$MERGED" 2>/dev/null || true
        $SUDO_CMD rm -rf "$UPPER" "$WORK" "$MERGED"
        $SUDO_CMD podman image umount "{{image_ref}}" 2>/dev/null || true
    }
    trap cleanup EXIT

    UPPER=$(mktemp -d); WORK=$(mktemp -d); MERGED=$(mktemp -d)
    $SUDO_CMD chmod 755 "$UPPER" "$WORK" "$MERGED"
    $SUDO_CMD mount -t overlay overlay \
        -o "lowerdir=${LOWER},upperdir=${UPPER},workdir=${WORK}" \
        "$MERGED"

    echo "==> Applying user.component xattrs via fakecap-restore..."
    $SUDO_CMD "$FAKECAP_RESTORE" files/fakecap-manifest.tsv "$MERGED"

    LOADED=$($SUDO_CMD podman run --rm \
        --security-opt label=type:unconfined_t \
        -v "${MERGED}:/chunkah:ro" \
        -e "CHUNKAH_CONFIG_STR=$CONFIG" \
        quay.io/coreos/chunkah:latest build --max-layers 128 \
        | $SUDO_CMD podman load)

    echo "$LOADED"

    NEW_REF=$(echo "$LOADED" | grep -oP '(?<=Loaded image: ).*' || \
              echo "$LOADED" | grep -oP '(?<=Loaded image\(s\): ).*')

    if [ -n "$NEW_REF" ] && [ "$NEW_REF" != "{{image_ref}}" ]; then
        echo "==> Retagging chunked image to {{image_ref}}..."
        $SUDO_CMD podman tag "$NEW_REF" "{{image_ref}}"
    fi

# ── bcvk (fast VM testing) ───────────────────────────────────────────
_ensure-bcvk:
    #!/usr/bin/env bash
    set -euo pipefail
    if command -v bcvk &>/dev/null; then
        exit 0
    fi
    echo "bcvk not found. Attempting to install via cargo..."
    if command -v cargo &>/dev/null; then
        cargo install --locked --git https://github.com/bootc-dev/bcvk bcvk
    else
        echo "ERROR: bcvk is not installed and cargo is not available for auto-install." >&2
        exit 1
    fi

[group('test')]
boot-fast: _ensure-bcvk
    #!/usr/bin/env bash
    set -euo pipefail

    SUDO_CMD=""
    if [ "$(id -u)" -ne 0 ]; then
        SUDO_CMD="sudo"
    fi

    if ! $SUDO_CMD podman image exists "{{image_name}}:{{image_tag}}"; then
        echo "ERROR: Image '{{image_name}}:{{image_tag}}' not found in podman." >&2
        echo "Run 'just build' first to build and export the OCI image." >&2
        exit 1
    fi

    echo "==> Booting {{image_name}}:{{image_tag}} in ephemeral VM (bcvk)..."
    $SUDO_CMD bcvk ephemeral run-ssh \
        --memory "{{vm_ram}}M" \
        --vcpus "{{vm_cpus}}" \
        "localhost/{{image_name}}:{{image_tag}}"

[group('info')]
inspect: _ensure-bcvk
    #!/usr/bin/env bash
    set -euo pipefail

    SUDO_CMD=""
    if [ "$(id -u)" -ne 0 ]; then
        SUDO_CMD="sudo"
    fi

    $SUDO_CMD bcvk images list

# ── Lint ─────────────────────────────────────────────────────────────
[group('test')]
lint:
    #!/usr/bin/env bash
    set -euo pipefail

    SUDO_CMD=""
    if [ "$(id -u)" -ne 0 ]; then
        SUDO_CMD="sudo"
    fi

    echo "==> Linting {{image_name}}:{{image_tag}} with bootc container lint..."
    $SUDO_CMD podman run --rm --privileged --pull=never \
        "{{image_name}}:{{image_tag}}" \
        bootc container lint

# ── Dashboard ────────────────────────────────────────────────────────
[group('build')]
dashboard:
    #!/usr/bin/env bash
    set -euo pipefail
    python3 "{{justfile_directory()}}/bst-dashboard.py" \
        --log /var/tmp/{{image_name}}-build.log \
        --target oci/{{image_name}}.bst \
        --project "{{justfile_directory()}}" &>/tmp/bst-dashboard.log &
    disown
    echo "Dashboard starting (log: /tmp/bst-dashboard.log)"
