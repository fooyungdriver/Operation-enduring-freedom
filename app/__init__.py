"""Red Arc Environmental — Ops Tool.

A small local application for Red Arc's hazardous-waste operations:
- reads generators / waste profiles / lab pack inventory from Zoho CRM,
- prints Uniform Hazardous Waste Manifests (EPA 8700-22) and LDR documents
  onto pre-printed forms via a dot-matrix printer,
- offers Claude-powered in-app skills (draft a profile from an SDS, suggest
  waste codes, check a manifest for completeness).

See README.md for setup. Nothing here talks to a server we host — Zoho is the
system of record and the only piece that runs in the cloud.
"""

__version__ = "0.1.0"
