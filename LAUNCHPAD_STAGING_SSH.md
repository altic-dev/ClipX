# Launchpad staging SSH — setup and recovery

This document describes how to connect to **Launchpad GA staging** over SSH, recover access when you are locked out of key-based login, and install a new SSH key. Follow your employer’s security policies; do not put passwords in scripts, repos, or chat.

## Connection details

| Item | Value |
|------|--------|
| Host | `global.stg.ga.launchpad.nvidia.com` |
| Port | `11122` |
| User | `bsubramaniam` |

Basic command:

```bash
ssh -p 11122 bsubramaniam@global.stg.ga.launchpad.nvidia.com
```

The server may offer **public key** and **password** authentication. If you have no working key, you will get a **password** prompt (use your **NVIDIA** credentials and complete MFA if required).

## Recommended: key on your own machine

For long-term access, generate a key **on your laptop or workstation**, not in a shared or cloud workspace.

1. Create a dedicated key (no passphrase is convenient but less secure; a passphrase is safer):

   ```bash
   ssh-keygen -t ed25519 -C "your.email@nvidia.com" -f ~/.ssh/launchpad_stg_ed25519
   ```

2. Try key login (after the public key is on the server — see below):

   ```bash
   ssh -i ~/.ssh/launchpad_stg_ed25519 -p 11122 -o IdentitiesOnly=yes \
     bsubramaniam@global.stg.ga.launchpad.nvidia.com
   ```

3. Optional `~/.ssh/config` entry:

   ```sshconfig
   Host launchpad-stg
     HostName global.stg.ga.launchpad.nvidia.com
     User bsubramaniam
     Port 11122
     IdentityFile ~/.ssh/launchpad_stg_ed25519
     IdentitiesOnly yes
   ```

   Then: `ssh launchpad-stg`

## Install your public key on the server

You need **one successful login** (password or existing key) to run these on the **remote** host.

### Option A — one line (replace with your own `.pub` line)

On the server, after you are logged in:

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo 'PASTE_ONE_LINE_FROM_YOUR_pubkey_FILE' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Your public key is a **single line** starting with `ssh-ed25519` or `ssh-rsa`.

### Option B — from your local machine (`ssh-copy-id`)

After password login works from your machine:

```bash
ssh-copy-id -i ~/.ssh/launchpad_stg_ed25519.pub -p 11122 \
  bsubramaniam@global.stg.ga.launchpad.nvidia.com
```

### Workspace-generated key (if you use the repo’s local `.ssh/`)

This repository’s `.ssh/` directory is **gitignored**. If you generated `launchpad_stg_ed25519` there, the public key file is:

`.ssh/launchpad_stg_ed25519.pub`

Copy its **one line** into `authorized_keys` as in Option A.

**Example public key** (workspace key created for this setup — use your own line if you generated a different key):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINbnXZznNFXMKlZmwa77YVWUobXrHsnn0BG/gHBdc5C/ bsubramaniam-launchpad-stg
```

## Verify key login

From your machine:

```bash
ssh -i ~/.ssh/launchpad_stg_ed25519 -p 11122 -o IdentitiesOnly=yes \
  bsubramaniam@global.stg.ga.launchpad.nvidia.com 'echo ok && whoami && hostname'
```

You should see `ok`, your username, and the host name **without** a password prompt.

## If you are completely locked out

- Use **corporate IT / account recovery** (password reset, MFA, VPN, jump host) for NVIDIA systems.
- Do **not** rely on `sshpass`, echoing passwords into `ssh`, or storing passwords in shell scripts — those leak via process listings, logs, and history.
- A colleague or platform admin with access can append your **public** key to your `~/.ssh/authorized_keys` if policy allows.

## Troubleshooting

| Symptom | Things to check |
|--------|-------------------|
| `Permission denied (publickey,password)` | No accepted key; password wrong; or account locked. Confirm VPN/network requirements for staging. |
| Key not tried | Use `-o IdentitiesOnly=yes` and `-i /path/to/private_key`. |
| Key ignored after install | On server: `chmod 700 ~/.ssh` and `chmod 600 ~/.ssh/authorized_keys`. Ensure the key line was not split across lines. |
| Host key warning | Compare fingerprint with an internal source of truth; only accept if you expect the host. |

## After you regain access

- Prefer **key-based** login for daily use.
- Changing your **password** or tightening **MFA** is done through your org’s normal account tools, not necessarily on the SSH server.
- Disabling **password** authentication for SSH is a **server configuration** change; only do that with the team that manages `sshd` on that host, and **after** key login is verified.
