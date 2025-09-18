# Security Model

This document summarizes the initial security model for the IDP demo.

- Authentication: JWT bearer tokens obtained via `/auth/token` (password flow).
- Authorization: Attribute‑based RBAC using `User.roles` (JSON array) with roles:
  - `superadmin`: global administrative privileges; bypasses org scoping.
  - `org_admin`: administers resources within their organization.
  - `designer`: can create/edit projects and upload artifacts within their org.
  - `researcher`: can create datasets/rulepacks and run evaluations within their org.
  - `reviewer`: read‑only access within their org.
- Tenancy: Every resource is associated to an organization (directly or indirectly via `Project`). All queries are scoped to the current user’s `org_id` unless the user is `superadmin`.
- Enforcement:
  - Route dependencies resolve the current user; routers validate org ownership and check roles before mutations.
  - Central audit middleware records who/what/when for every request, including sanitized request body (without passwords) and response status.
- Storage:
  - Secrets are read from environment.
  - Uploaded objects stored in S3/MinIO; keys are prefixed by project and do not contain sensitive data.

Hardening notes
- Passwords are hashed with bcrypt.
- Tokens use HMAC (HS256); rotate `JWT_SECRET` in production.
- CORS is limited to the development web origin.
- Future: rate limiting, refresh tokens, CSRF protections for cookie‑based auth, and principle of least privilege for service accounts.

