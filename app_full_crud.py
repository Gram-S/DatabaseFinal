import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# --- Config & env ---
st.set_page_config(page_title="Haunted DB Viewer", page_icon="👻", layout="wide")
load_dotenv()

PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
PGDATABASE = os.getenv("PGDATABASE")
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")

if not all([PGDATABASE, PGUSER, PGPASSWORD]):
    st.error("Missing DB credentials. Please set PGDATABASE, PGUSER, and PGPASSWORD in your .env file.")
    st.stop()

DB_URL = f"postgresql+psycopg2://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
engine = create_engine(DB_URL, pool_pre_ping=True)

# --- Session flash ---
st.session_state.setdefault("just_inserted", None)
st.session_state.setdefault("just_updated", None)
st.session_state.setdefault("just_deleted", None)

st.title("👻 Haunted Database Viewer")
st.caption("Full CRUD demo for monsters (PostgreSQL).")

# --- Helpers ---
def fetch_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})
    except Exception as e:
        st.error(f"Query failed: {e}")
        return pd.DataFrame()

def fetch_houses() -> pd.DataFrame:
    return fetch_df("SELECT id, house_name, location, built_year FROM haunted_houses ORDER BY id")

def fetch_monsters(limit: int) -> pd.DataFrame:
    sql = 'SELECT id, name, "type" AS monster_type, scare_level, house_id FROM monsters ORDER BY id LIMIT :lim'
    return fetch_df(sql, {"lim": int(limit)})

def insert_monster(name: str, mtype: str | None, scare: int, house_id: int):
    sql = '''
        INSERT INTO monsters(name, "type", scare_level, house_id)
        VALUES (:n, :t, :s, :hid)
        RETURNING id, name, "type" AS monster_type, scare_level, house_id
    '''
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params={"n": name, "t": mtype, "s": scare, "hid": house_id})
    return df.iloc[0].to_dict() if not df.empty else None

def update_monster(mid: int, name: str, mtype: str | None, scare: int, house_id: int):
    sql = '''
        UPDATE monsters
        SET name = :n, "type" = :t, scare_level = :s, house_id = :hid
        WHERE id = :mid
        RETURNING id, name, "type" AS monster_type, scare_level, house_id
    '''
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params={"mid": int(mid), "n": name, "t": mtype, "s": scare, "hid": house_id})
    return df.iloc[0].to_dict() if not df.empty else None

def delete_monster(mid: int):
    sql = '''
        DELETE FROM monsters
        WHERE id = :mid
        RETURNING id, name, "type" AS monster_type, scare_level, house_id
    '''
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params={"mid": int(mid)})
    return df.iloc[0].to_dict() if not df.empty else None

# --- Sidebar ---
with st.sidebar:
    st.header("Options")
    row_limit = st.number_input("Row limit", min_value=1, max_value=2000, value=200, step=50)
    show_join = st.checkbox("Show joined view", value=True)

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["🏚️ Houses", "👹 Monsters (CRUD)", "🔗 Joined"])

with tab1:
    st.subheader("Haunted Houses")
    houses = fetch_houses()
    st.dataframe(houses.head(int(row_limit)), use_container_width=True)

with tab2:
    st.subheader("Monsters")

    # Flash messages
    for key, icon, msg in [
        ("just_inserted", "✅", "Inserted"),
        ("just_updated", "✏️", "Updated"),
        ("just_deleted", "🗑️", "Deleted")
    ]:
        if st.session_state.get(key):
            rec = st.session_state[key]
            st.success(f"{icon} {msg} monster: {rec['name']} (ID {rec['id']})")
            st.session_state[key] = None

    monsters = fetch_monsters(int(row_limit))
    st.dataframe(monsters, use_container_width=True)

    # House choices
    houses = houses if not houses.empty else fetch_houses()
    house_choices = {int(r.id): f"{int(r.id)} — {r.house_name or 'Unnamed'} ({r.location or 'Unknown'})" for _, r in houses.iterrows()}

    # INSERT
    st.markdown("### ➕ Insert")
    with st.form("insert_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Name*", placeholder="Boo Radley")
            mtype = st.text_input("Type (optional)", placeholder="ghost / vampire / …")
        with c2:
            scare = st.number_input("Scare level* (1–10)", 1, 10, 5, 1)
            hid = st.selectbox("House*", options=list(house_choices.keys()), format_func=lambda k: house_choices[k])
        if st.form_submit_button("Insert"):
            if not name.strip():
                st.warning("Name is required.")
            else:
                rec = insert_monster(name.strip(), mtype.strip() or None, int(scare), int(hid))
                if rec:
                    st.session_state.just_inserted = rec
                    st.rerun()

    # UPDATE
    st.markdown("### ✏️ Update")
    if monsters.empty:
        st.caption("No monsters to update.")
    else:
        monster_choices = {int(r.id): f"{int(r.id)} — {r['name']} (scare {int(r['scare_level'])})" for _, r in monsters.iterrows()}
        sel_id = st.selectbox("Monster", options=list(monster_choices.keys()), format_func=lambda k: monster_choices[k], key="upd_sel")
        current = monsters[monsters["id"] == sel_id].iloc[0]

        with st.form("update_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("Name", current["name"])
                new_type = st.text_input("Type", current["monster_type"] or "")
            with c2:
                new_scare = st.number_input("Scare level (1–10)", 1, 10, int(current["scare_level"]), 1)
                new_house = st.selectbox("House", options=list(house_choices.keys()),
                                         index=list(house_choices.keys()).index(int(current["house_id"])),
                                         format_func=lambda k: house_choices[k])
            if st.form_submit_button("Update"):
                rec = update_monster(sel_id, new_name.strip(), new_type.strip() or None, int(new_scare), int(new_house))
                if rec:
                    st.session_state.just_updated = rec
                    st.rerun()

    # DELETE
    st.markdown("### 🗑️ Delete")
    if monsters.empty:
        st.caption("No monsters to delete.")
    else:
        monster_choices = {int(r.id): f"{int(r.id)} — {r['name']} (scare {int(r['scare_level'])})" for _, r in monsters.iterrows()}
        colA, colB = st.columns([3, 2])
        with colA:
            del_id = st.selectbox("Select monster", options=list(monster_choices.keys()),
                                  format_func=lambda k: monster_choices[k], key="del_sel")
        with colB:
            confirm = st.checkbox("Confirm deletion", key="del_confirm")

        if st.button("Delete selected"):
            if not confirm:
                st.warning("Please confirm before deleting.")
            else:
                rec = delete_monster(int(del_id))
                if rec:
                    st.session_state.just_deleted = rec
                    st.rerun()

with tab3:
    st.subheader("Joined view")
    if show_join:
        sql = '''
            SELECT m.id, m.name, m."type" AS monster_type, m.scare_level,
                   h.house_name, h.location, h.built_year
            FROM monsters m
            JOIN haunted_houses h ON m.house_id = h.id
            ORDER BY m.id
            LIMIT :lim
        '''
        st.dataframe(fetch_df(sql, {"lim": int(row_limit)}), use_container_width=True)
    else:
        st.info("Enable the joined view toggle in the sidebar.")
