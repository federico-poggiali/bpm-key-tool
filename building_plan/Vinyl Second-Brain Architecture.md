# Vinyl Second-Brain Architecture

Oct 10, 2026 · @Someone

A system that takes a newly bought record from a Discogs link, analyzes every track for BPM and key, stores it all in a queryable database, and projects it into Obsidian as a read-mostly second brain for notes, tags, and discovery.

## Overview

&#91;embedded content: pipeline · intake to database and Obsidian\]

One event, two branches. The Discogs link triggers analysis once; after that, Discogs collection and the database are written independently, and only the database ever gets edited. Obsidian and its markdown files are generated output, not a second place to write.

## Data model

Four entities: records, tracks under them, notes attached to either, and tags. Notes are deliberately one flexible table rather than several, since new note types will keep showing up.

| Entity | Key fields | Notes |
| --- | --- | --- |
| Record | Discogs release ID, artist, title, label, year, format | One row per release; mirrors the Discogs collection entry |
| Track | Position (e.g. A1), title, BPM, key, duration, confidence score | Child of a record; holds the analysis tool's raw output |
| Note | Type, body text, embedding vector, timestamp, parent (record or track) | Type is an open tag, not a fixed enum: prose, cue-points, shelf location, purchase info, condition, anything new |
| Tag | Name, parent (record or track) | Many-to-many; freeform or controlled vocabulary, your choice |

Two design choices worth flagging. First, notes attach to either a record or a track, since some things are release-level (where you bought it) and some are track-level (cue points, a DJ note on one song). Second, only the `prose`-type notes get embedded for semantic search; structured notes like shelf location stay exact-match fields, there's no meaning to search for in a shelf number.

## Role split: database vs. Obsidian

The database is the single place where writing happens. Obsidian is a generated, read-mostly view on top of it. This avoids two-way sync between markdown files and a database, which is the hardest part to get right in this kind of system.

|  | Database (your app) | Obsidian |
| --- | --- | --- |
| Owns | All structured fields and all note text | Nothing; it only displays |
| Editing | Yes, this is where you write | Read-only in principle; treat edits there as disposable |
| Query style | Exact filters: BPM range, key, tag, full-text | Dataview syntax over frontmatter; good for browsing, not precision |
| Can hold | Only records you own or have analyzed | Also wantlist items, records you don't own, speculative notes |
| Regeneration | N/A | One markdown file per record, rewritten whenever the database changes |

The rule that keeps this simple: your sync script only ever overwrites the frontmatter block of a generated note, never the body. In practice this works best if the body is treated as pure display too, for example rendered from the database's note text into the markdown body on every regen, rather than hand-edited in Obsidian at all. If you want Obsidian itself to be writable someday, that's a bigger step (true two-way sync) and worth treating as a separate, later decision rather than building it in now.

## Semantic search over notes

Dataview and ordinary full-text search only match literal words, so "banging track" and "huge energy, crowd goes off" look unrelated to them even though they mean the same thing. Meaning-based search needs embeddings, which is a separate, small pipeline:

1. Whenever a prose note is saved, send its text to an embedding model (OpenAI's API is simplest; a local open-source model works too and is free).
2. Store the resulting vector alongside the note in the database. With SQLite, the `sqlite-vec` extension makes this a single extra column.
3. To search, embed the query the same way and ask the database for the closest stored vectors, one function call does the similarity math.

Realistically 50 to 100 lines of code, most of it plumbing. The only real design question is when to (re-)run the embedding: on every save, or on a schedule. This lives entirely in the database layer; Obsidian never needs to know it exists, though a search box in the app can jump straight to the matching record's note.

## Open decisions

- Note types: start with a small fixed set (prose, cue-points, location, purchase info) or leave the type field fully open from day one?
- Markdown body in Obsidian: fully auto-rendered from the database on every regen, or allow light hand-editing that gets discarded on next sync?
- Embedding provider: OpenAI API (simplest, small ongoing cost) or a local model (free, more setup)?
- Tag vocabulary: freeform tags or a controlled list pulled from Discogs genres and styles?
- Obsidian plugins: adopt Dataview only, or also Smart Connections for in-vault semantic search, versus keeping all search inside your own app?
- Non-owned records: should wantlist or "considering" records get their own flag in the database too, or live only in Obsidian as you described?
