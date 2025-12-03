import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import URL
from dotenv import load_dotenv

# --------------- Page & env ---------------
st.set_page_config(page_title="PTMsToPathways DB Viewer", page_icon="👻", layout="wide")
load_dotenv()

PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
PGDATABASE = os.getenv("PGDATABASE")
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")
PGSSLMODE = os.getenv("PGSSLMODE", "require")  # Neon needs SSL; default to 'require'

if not all([PGDATABASE, PGUSER, PGPASSWORD]):
    st.error("Missing DB credentials. Please set PGDATABASE, PGUSER, and PGPASSWORD in your .env file.")
    st.stop()

def make_url() -> URL:
    # NOTE: no 'options' here; Neon pooler rejects startup options.
    return URL.create(
        "postgresql+psycopg2",
        username=PGUSER,
        password=PGPASSWORD,
        host=PGHOST,
        port=int(PGPORT),
        database=PGDATABASE,
        query={
            "connect_timeout": "5",   # fail fast instead of hanging
            "sslmode": PGSSLMODE      # 'require' for Neon
        },
    )

@st.cache_resource
def get_engine():
    engine = create_engine(
        make_url(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
        pool_timeout=5,
        pool_recycle=1800,
    )

    # Apply per-connection settings after the pool hands out a DBAPI conn.
    # Neon pooler *does* allow SET after connect, just not startup 'options'.
    @event.listens_for(engine, "connect")
    def _set_statement_timeout(dbapi_connection, connection_record):
        with dbapi_connection.cursor() as cur:
            # 8000 ms = 8s; adjust as you like
            cur.execute("SET statement_timeout TO 8000")

    return engine

engine = get_engine()

def fetch_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})
    except Exception as e:
        st.error(f"DB error: {e}")
        return pd.DataFrame()

# SQL functions
def insert_ptm(ptm: str, drug: str, reaction_score: int):
    sql = '''
        INSERT INTO ptmdataset(ptm, drug, reaction_score)
        VALUES (:n, :t, :s)
        RETURNING ptm, drug, reaction_score AS ptm, drug, reaction_score
    '''
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params={"n": ptm, "t": drug, "s": reaction_score})
    return df.iloc[0].to_dict() if not df.empty else None

# --------------- UI ---------------
st.title("👻 PTMsToPathways DB Viewer")
st.caption("Neon-ready: SSL on, statement_timeout set after connect, and fast-fail timeouts.")

with st.sidebar:
    row_limit = st.number_input("Row limit", min_value=1, max_value=2000, value=200, step=50)

tab1, tab2, tab3 = st.tabs(["🏚️ ptmdataset", "👹 ptm_correlation_matrix", "🔗 common_clusters"])

with tab1:
    st.subheader("ptmdataset")
    sql = "SELECT ptm, drug, reaction_score FROM ptmdataset ORDER BY ptm LIMIT :lim"
    st.dataframe(fetch_df(sql, {"lim": int(row_limit)}), use_container_width=True)
    
    st.markdown("### ➕ Insert")
    with st.form("insert_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            ptm = st.text_input("ptm*", placeholder="AARS ubi k474")
            drug = st.text_input("drug", placeholder="H3122SEPTM_pTyr.PR2")
            reaction_score = st.number_input("reaction_score", placeholder="0")
        if st.form_submit_button("Insert"):
            if not ptm.strip() or not drug.strip():
                st.warning("Please fill out all required fields!")        
            else:
                rec = insert_ptm(ptm.strip(), drug.strip(), int(reaction_score))
                if rec:
                    st.session_state.just_inserted = rec
                    st.rerun()

with tab2:
    st.subheader("ptm_correlation_matrix")
    sql = 'SELECT ptm1, ptm2, spearman_score FROM ptm_correlation_matrix ORDER BY spearman_score LIMIT :lim'
    st.dataframe(fetch_df(sql, {"lim": int(row_limit)}), use_container_width=True)

with tab3:
    st.subheader("common_clusters")
    sql = "SELECT clusterid, ptmsincluster FROM common_clusters"
    st.dataframe(fetch_df(sql, {"lim": int(row_limit)}), use_container_width=True)

st.markdown("---")
st.caption(f"Connecting to {PGHOST}:{PGPORT}/{PGDATABASE} as {PGUSER} (sslmode={PGSSLMODE}).")
