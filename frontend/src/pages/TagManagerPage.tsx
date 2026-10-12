import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type TagGroup } from "../api/api";
import { useTagGroups } from "../hooks";
import styles from "./TagManagerPage.module.css";

const BLURB: Record<string, string> = {
  Energy: "How hard a track hits: ambient, groove, peak.",
  Atmosphere: "Mood and texture: dreamy, dark, sunny.",
  "Set role": "Where it goes in a set: opener, builder, closer.",
};

/** One line of text plus a button, used for adding tags and groups. */
function AddForm({ label, placeholder, onAdd }: { label: string; placeholder: string; onAdd: (name: string) => void }) {
  const [text, setText] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (text.trim()) onAdd(text.trim());
    setText("");
  };
  return (
    <form className={styles.add} onSubmit={submit}>
      <input className="field-input" value={text} placeholder={placeholder} aria-label={label} maxLength={50} onChange={(e) => setText(e.target.value)} />
      <button className="ghost small" type="submit" disabled={!text.trim()}>Add</button>
    </form>
  );
}

function TagRow({ group, groups, tag, rename, move, remove }: {
  group: TagGroup; groups: TagGroup[]; tag: TagGroup["tags"][number];
  rename: (id: number, name: string) => void; move: (id: number, groupId: number) => void; remove: (id: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(tag.name);
  const [confirm, setConfirm] = useState(false);
  const used = tag.record_count + tag.track_count;
  const save = (e: FormEvent) => {
    e.preventDefault();
    setEditing(false);
    if (text.trim() && text.trim().toLowerCase() !== tag.name) rename(tag.id, text.trim());
    else setText(tag.name);
  };
  return (
    <li className={styles.tag}>
      {editing ? (
        <form onSubmit={save} className={styles.rename}>
          <input className="field-input" autoFocus value={text} aria-label={`Rename ${tag.name}`} onChange={(e) => setText(e.target.value)}
            onBlur={save} onKeyDown={(e) => { if (e.key === "Escape") { setText(tag.name); setEditing(false); } }} />
        </form>
      ) : (
        <button type="button" className={styles.name} onClick={() => setEditing(true)} title="Rename">{tag.name}</button>
      )}
      <span className="micro" title={`${tag.record_count} records · ${tag.track_count} tracks`}>{used}</span>
      <select className={styles.move} value={group.id} aria-label={`Move ${tag.name} to another group`} onChange={(e) => move(tag.id, Number(e.target.value))}>
        {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
      </select>
      {confirm ? (
        <>
          <button type="button" className="ghost small danger" onClick={() => remove(tag.id)}>Remove from {used} {used === 1 ? "item" : "items"}</button>
          <button type="button" className="ghost small" onClick={() => setConfirm(false)}>Keep</button>
        </>
      ) : (
        <button type="button" className={styles.x} aria-label={`Delete tag ${tag.name}`} onClick={() => (used > 0 ? setConfirm(true) : remove(tag.id))}>×</button>
      )}
    </li>
  );
}

/** A change to groups or tags: the server answers with the fresh list, and everything that shows tags refreshes. */
function useGroupMutation<A>(fn: (a: A) => Promise<{ items: TagGroup[] }>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (data) => {
      client.setQueryData(["tag-groups"], data.items);
      for (const key of ["tags", "records", "tracks"]) client.invalidateQueries({ queryKey: [key] });
    },
  });
}

/** Design the tags: fixed groups for energy, atmosphere and set role, plus groups of your own. */
export default function TagManagerPage() {
  const groups = useTagGroups();
  const createGroup = useGroupMutation((name: string) => api.createTagGroup(name));
  const renameGroup = useGroupMutation(({ id, name }: { id: number; name: string }) => api.renameTagGroup(id, name));
  const deleteGroup = useGroupMutation((id: number) => api.deleteTagGroup(id));
  const createTag = useGroupMutation(({ groupId, name }: { groupId: number; name: string }) => api.createTagDef(groupId, name));
  const updateTag = useGroupMutation(({ id, ...body }: { id: number; name?: string; group_id?: number }) => api.updateTagDef(id, body));
  const deleteTag = useGroupMutation((id: number) => api.deleteTagDef(id));
  const [dropping, setDropping] = useState<number | null>(null);
  const items = groups.data ?? [];

  return (
    <div className={styles.page}>
      <header>
        <span className="micro">tag manager</span>
        <h1>Tags</h1>
        <p className={styles.hint}>Design your tags here, then put them on records and tracks. A name is used once across all groups.</p>
      </header>

      {groups.isLoading && <p className={styles.hint}>Loading…</p>}
      {items.map((g) => (
        <section key={g.id} className={styles.group} aria-label={g.name}>
          <div className={styles.groupHead}>
            <h2>{g.name}</h2>
            {g.fixed ? <span className="micro">{BLURB[g.name] ?? "fixed"}</span> : (
              <span className={styles.groupActions}>
                <button type="button" className="ghost small" onClick={() => {
                  const name = window.prompt("Rename group", g.name);
                  if (name?.trim() && name.trim() !== g.name) renameGroup.mutate({ id: g.id, name: name.trim() });
                }}>Rename</button>
                {dropping === g.id ? (
                  <>
                    <button type="button" className="ghost small danger" onClick={() => { deleteGroup.mutate(g.id); setDropping(null); }}>
                      Delete group and its {g.tags.length} tags
                    </button>
                    <button type="button" className="ghost small" onClick={() => setDropping(null)}>Keep</button>
                  </>
                ) : (
                  <button type="button" className="ghost small" onClick={() => (g.tags.length ? setDropping(g.id) : deleteGroup.mutate(g.id))}>Delete</button>
                )}
              </span>
            )}
          </div>
          {g.tags.length === 0 ? <p className={styles.hint}>No tags yet.</p> : (
            <ul className={styles.tags}>
              {g.tags.map((t) => (
                <TagRow key={t.id} group={g} groups={items} tag={t}
                  rename={(id, name) => updateTag.mutate({ id, name })}
                  move={(id, groupId) => updateTag.mutate({ id, group_id: groupId })}
                  remove={(id) => deleteTag.mutate(id)} />
              ))}
            </ul>
          )}
          <AddForm label={`New tag in ${g.name}`} placeholder="new tag" onAdd={(name) => createTag.mutate({ groupId: g.id, name })} />
        </section>
      ))}

      <section className={styles.group} aria-label="New group">
        <div className={styles.groupHead}><h2>New group</h2><span className="micro">your own way of sorting tracks</span></div>
        <AddForm label="New group name" placeholder="e.g. Occasion" onAdd={(name) => createGroup.mutate(name)} />
      </section>
    </div>
  );
}
