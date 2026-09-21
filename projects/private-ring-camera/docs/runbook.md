# Private Camera Operations Runbook

This runbook covers the local-first camera deployment after the Pi, Mac, and
operator phone are enrolled in Tailscale.

## Normal access

- Open `https://tindols-macbook-pro.tail133ca1.ts.net/` only after the viewing
  device is connected to the `stratiosai@gmail.com` tailnet.
- Sign in with the camera administrator account. Do not put the password in
  Git, shell history, tickets, or chat.
- Keep Tailscale Funnel disabled. The router must have no port-forwarding or
  DMZ entry for the Pi or Mac.

## Lost phone or laptop

1. In the Tailscale admin console, revoke the lost device immediately.
2. Use the camera UI's **Log out all devices** action to invalidate active web
   sessions.
3. Sign in again only from a trusted device, then rotate the camera admin
   password if the lost device may have had it saved.
4. Confirm the device no longer appears in `tailscale status` on the Mac.

## Credential rotation

1. Run the local password-reset command on the Mac; never print the new value.
2. The reset must revoke existing camera sessions.
3. If a Pi ingest or live token is suspected, generate replacement tokens in
   the private application-data directory and redeploy the user services.
4. Verify that the old token is rejected before deleting the old secret.

## Pi or Mac recovery

- Pi services should be enabled user services with lingering enabled:
  `edge-camera-capture`, `edge-camera-live`, and `edge-camera-agent`.
- The Pi may buffer up to one hour or 2 GB while the Mac is unavailable; after
  reconnection, confirm the buffer drains and check for duplicate
  `(started_at, ended_at, sha256)` rows.
- The Mac archive is outside Git and iCloud at
  `~/Library/Application Support/StratiosAI/edge-ai-camera/archive/`.
- If the Mac server is unavailable, do not expose port 8443 through the router;
  restore the LaunchAgent and use the Tailscale URL after it returns.

## Privacy and deletion

- Keep the camera aimed at the controlled test area until privacy masks and
  outdoor/shared-space review are complete.
- Use confirmed deletion in the authenticated UI and verify both media and
  timeline metadata are gone.
- Do not copy recordings to Photos, iCloud, or another cloud service unless a
  separate privacy and cost decision is recorded.

