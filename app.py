"""Talk-to-Task web UI. Run with: streamlit run app.py"""

import datetime
from urllib.parse import quote

import streamlit as st

import talk_to_task as t

st.set_page_config(page_title="Talk-to-Task", page_icon="🐝", layout="wide")

st.title("🐝 Talk-to-Task")
st.caption(
    "Promises you made out loud, captured by Bee, turned into tasks by Claude on Amazon Bedrock."
)

# Tasks persist in a local file between runs (never in demo mode).
if "store" not in st.session_state:
    st.session_state["store"] = t.load_store()
    st.session_state["persist"] = True
    st.session_state["convs"] = []


def save() -> None:
    if st.session_state["persist"]:
        t.save_store(st.session_state["store"])


with st.sidebar:
    st.header("Source")
    demo = st.toggle(
        "Demo mode (sample data)",
        value=False,
        help="Use built-in sample text instead of live Bee data.",
    )
    hours = st.slider(
        "Look back (hours)",
        1,
        10,
        10,
        help="Only include conversations from the last N hours.",
    )
    contacts = st.text_input(
        "People you talk to (optional)",
        value=t.CONTACTS,
        placeholder="Priya, Rahul, Meera",
        help="Helps fix names that speech-to-text mishears.",
    )
    run = st.button("Fetch & analyze", type="primary", use_container_width=True)
    st.caption(
        "Only transcript text is sent to the model. Tasks are saved locally in tasks_store.json."
    )
    if st.button("Clear saved tasks", use_container_width=True):
        st.session_state["store"] = []
        st.session_state["persist"] = True
        save()
        st.rerun()

if run:
    try:
        with st.spinner("Reading your Bee conversations..."):
            convs = t.fetch_conversations(demo, hours)
        with st.spinner("Finding your promises..."):
            new_tasks = t.extract_tasks(convs, contacts)
        base = [] if demo else t.load_store()
        st.session_state["store"] = t.merge_tasks(base, new_tasks)
        st.session_state["persist"] = not demo
        st.session_state["convs"] = convs
        save()
    except FileNotFoundError:
        st.error(
            "The `bee` command wasn't found. Make sure the Bee CLI is installed and on your PATH."
        )
    except Exception as e:  # show a readable error instead of a traceback
        st.error(f"Something went wrong: {e}")

store = st.session_state["store"]
convs = st.session_state["convs"]
today = datetime.date.today().isoformat()


def render_task(task: dict, group: str) -> None:
    with st.container(border=True):
        done = st.checkbox(
            f"**{task['task']}**", value=task["done"], key=f"done-{group}-{task['key']}"
        )
        if done != task["done"]:
            task["done"] = done
            save()
            st.rerun()
        bits = []
        if task.get("person"):
            bits.append(f"👤 {task['person']}")
        bits.append(f"📅 {task.get('due') or 'no date'}")
        if task.get("confidence") is not None:
            conf = int(float(task["confidence"]) * 100)
            bits.append(
                f"confidence {conf}%" + (" ⚠️ check this one" if conf < 70 else "")
            )
        st.caption("  ·  ".join(bits))

        draft = task.get("draft_message")
        if draft:
            st.caption("Draft follow-up (use the copy icon):")
            st.code(draft, language=None)

        cols = st.columns(4)
        if draft:
            cols[0].link_button("💬 WhatsApp", f"https://wa.me/?text={quote(draft)}")
            cols[1].link_button(
                "✉️ Email", f"mailto:?subject={quote(task['task'])}&body={quote(draft)}"
            )
        if task.get("due"):
            cols[2].download_button(
                "📅 Calendar",
                data=t.tasks_to_ics([task]),
                file_name="promise.ics",
                mime="text/calendar",
                key=f"ics-{group}-{task['key']}",
            )
        if task.get("in_bee"):
            cols[3].caption("✅ In Bee todos")
        elif cols[3].button("➕ Add to Bee", key=f"bee-{group}-{task['key']}"):
            ok, message = t.add_to_bee(task)
            if ok:
                task["in_bee"] = True
                save()
                st.rerun()
            else:
                st.error(f"Couldn't add to Bee: {message}")


if not store:
    st.info("Click **Fetch & analyze** in the sidebar to get started.")
else:
    open_tasks = [x for x in store if not x["done"]]
    done_tasks = [x for x in store if x["done"]]
    carried = [x for x in open_tasks if x.get("added_at", today) < today]

    buckets = {"Overdue": [], "Today": [], "Tomorrow": [], "Later": [], "No date": []}
    for task in open_tasks:
        buckets[t.due_bucket(task.get("due"))].append(task)

    st.subheader("Morning summary")
    cols = st.columns(5)
    cols[0].metric("Open promises", len(open_tasks))
    cols[1].metric("Overdue", len(buckets["Overdue"]))
    cols[2].metric("Due today", len(buckets["Today"]))
    cols[3].metric("Due tomorrow", len(buckets["Tomorrow"]))
    cols[4].metric(
        "Carried over", len(carried), help="Open promises from earlier days."
    )

    if any(x.get("due") for x in open_tasks):
        st.download_button(
            "📅 Add all open tasks to calendar (.ics)",
            data=t.tasks_to_ics(open_tasks),
            file_name="promises.ics",
            mime="text/calendar",
            key="ics-all",
        )

    for name, items in buckets.items():
        if not items:
            continue
        st.subheader(name)
        for task in sorted(items, key=lambda x: x.get("due") or "9999"):
            render_task(task, name)

    if done_tasks:
        with st.expander(f"Done ({len(done_tasks)})"):
            for task in done_tasks:
                render_task(task, "done")

if convs:
    with st.expander("What Bee heard"):
        for c in convs:
            st.markdown(f"**{c['title']}** — {c['start']}")
            st.text(c["text"])
