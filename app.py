"""Talk-to-Task web UI. Run with: streamlit run app.py"""

import streamlit as st

import talk_to_task as t

st.set_page_config(page_title="Talk-to-Task", page_icon="🐝", layout="wide")

st.title("🐝 Talk-to-Task")
st.caption(
    "Promises you made out loud, captured by Bee, turned into tasks by Claude on Amazon Bedrock."
)

with st.sidebar:
    st.header("Source")
    demo = st.toggle(
        "Demo mode (sample data)",
        value=False,
        help="Use built-in sample text instead of live Bee data.",
    )
    run = st.button("Fetch & analyze", type="primary", use_container_width=True)
    st.caption(
        "Reads the last ~10 hours of your Bee conversations. Only transcript text is sent to the model."
    )

if run:
    try:
        with st.spinner("Reading your Bee conversations..."):
            convs = t.fetch_conversations(demo)
        with st.spinner("Finding your promises..."):
            tasks = t.extract_tasks(convs)
        st.session_state["convs"] = convs
        st.session_state["tasks"] = tasks
    except FileNotFoundError:
        st.error(
            "The `bee` command wasn't found. Make sure the Bee CLI is installed and on your PATH."
        )
    except Exception as e:  # show a readable error instead of a traceback
        st.error(f"Something went wrong: {e}")

tasks = st.session_state.get("tasks")
convs = st.session_state.get("convs", [])

if tasks is None:
    st.info("Click **Fetch & analyze** in the sidebar to get started.")
else:
    buckets = {"Overdue": [], "Today": [], "Tomorrow": [], "Later": [], "No date": []}
    for task in tasks:
        buckets[t.due_bucket(task.get("due"))].append(task)

    st.subheader("Morning summary")
    cols = st.columns(4)
    cols[0].metric("Total promises", len(tasks))
    cols[1].metric("Overdue", len(buckets["Overdue"]))
    cols[2].metric("Due today", len(buckets["Today"]))
    cols[3].metric("Due tomorrow", len(buckets["Tomorrow"]))

    if not tasks:
        st.success("No commitments found in this window.")

    for name, items in buckets.items():
        if not items:
            continue
        st.subheader(name)
        for i, task in enumerate(sorted(items, key=lambda x: x.get("due") or "9999")):
            with st.container(border=True):
                st.checkbox(f"**{task['task']}**", key=f"{name}-{i}")
                bits = []
                if task.get("person"):
                    bits.append(f"👤 {task['person']}")
                bits.append(f"📅 {task.get('due') or 'no date'}")
                if task.get("confidence") is not None:
                    bits.append(f"confidence {int(float(task['confidence']) * 100)}%")
                st.caption("  ·  ".join(bits))
                if task.get("draft_message"):
                    st.caption("Draft follow-up (use the copy icon):")
                    st.code(task["draft_message"], language=None)

    with st.expander("What Bee heard"):
        for c in convs:
            st.markdown(f"**{c['title']}** — {c['start']}")
            st.text(c["text"])
