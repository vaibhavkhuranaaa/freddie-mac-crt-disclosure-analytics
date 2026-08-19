# Promote verified hosted candidate

## Decision

Promote the exact authenticated P7 preview of the M13 aggregate-only candidate to the existing Vercel production alias after content, header, boundary, and browser verification.

## Why

The preview served the reviewed static artifacts, excluded the private integrity manifest, preserved production security headers, and completed the dashboard workflow without a runtime API or restricted data. Existing free Vercel capacity kept incremental cost at zero.

## Rollback

Retain the previously READY production deployment and exact rollback command in the private operations record. Reassign the production alias to that deployment if reachability, parity, boundary, or interaction verification fails.

## Not authorized

No repository publication or push, portfolio-site change, new cloud resource, paid spend, or expanded data exposure.

## Limitations

Hosted verification covers Chromium and static HTTP behavior. It does not establish representative usability, cross-browser behavior, field performance, or concurrent capacity.
