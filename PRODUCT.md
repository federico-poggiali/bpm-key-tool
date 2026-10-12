# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

A vinyl DJ/collector who digs for records and preps sets, working on a Mac with the app on localhost (no login). Single user today; sharing or hosting for others is a possible later step, so nothing should make that impossible. Secondary jobs: keeping notes and tags on records and tracks, and printing sleeve/crate labels.

## Product Purpose

Spin Count ("Vinyl Second-Brain") is a personal vinyl library. Paste a Discogs link and the record, its tracklist and every track's BPM and key (Camelot or musical) land in the library, with no audio files needed. The main point is digging and set prep: find records by tempo, key and tag. Success is going from a Discogs link to a searchable, set-ready record in seconds.

## Positioning

BPM and key come from the bpmkey engine using only the Discogs link (online databases first, then audio it finds itself); the user's own rips optionally override. The library is also generated into an Obsidian vault, so it doubles as a second brain.

## Operating Context

- Discogs personal token in `.env`; owned records are also added to the user's Discogs collection (never removed, never duplicated).
- SQLite is the only place anything is written; the Obsidian vault (`vault/`, Dataview) is generated output and overwritten on sync.
- Optional audio in `audio/<discogs release id>/`, matched to tracks by position then title.
- Labels: two 62 × 40 mm labels per record (696 × 472 px, 1-bit PNG) for a Brother QL; download-only for now, direct printing later.

## Capabilities and Constraints

- Intake from Discogs release or master URL; statuses such as owned, wantlist, considering.
- Filters by BPM range, key (musical or Camelot), tags, status and free text; BPM and key must match on the same track.
- Manual BPM/key entry is always possible, marked *manual*, and never overwritten by re-analysis.
- Keyboard-first: `n` adds a record, `/` searches.
- Stack already exists: React frontend served by a FastAPI backend on one port, SQLite.
- Country and category are deliberately not stored. Undecided: sharing/hosting model, direct Brother QL printing.

## Brand Commitments

Name: Spin Count. Visual identity is not fixed by this file; see the frontend tokens and the memory note that the earlier bpmkey palette was deliberately replaced.

## Evidence on Hand

Real Discogs fixtures in `backend/tests/fixtures/`, a working library under `backend/data/vinyl.db`, and a generated vault in `vault/`. No user testimonials or usage data exist; do not invent any.

## Product Principles

1. Digging speed first: tempo, key and tag search must be reachable by keyboard and answer instantly.
2. The database is the single source of truth; generated outputs (vault, labels) never become a second place to edit.
3. The user's manual input always wins over automatic analysis.
4. Never surprise the user's Discogs collection or their own files.
5. Single-user simplicity now, without foreclosing sharing later.

## Accessibility & Inclusion

Dark and light themes are both supported, and the axe e2e tests enforce contrast in each. Keep keyboard operability and visible focus for every control.
