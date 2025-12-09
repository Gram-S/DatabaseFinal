import os
import random 
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
def insert_ptm(ptm: str):
    sql = '''
        INSERT INTO ptms(ptm)
        VALUES (:n)
        RETURNING ptm AS ptm
    '''
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params={"n": ptm})
    return df.iloc[0].to_dict() if not df.empty else None

def update_ptm(current: str, new: str):
    sql = '''
        UPDATE ptms
        SET ptm = :n
        WHERE ptm = :c
        RETURNING ptm AS ptm
    '''
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params={"c": current, "n": new})
    return df.iloc[0].to_dict() if not df.empty else None
    
def delete_ptm(mid: str):
    sql = '''
        DELETE FROM ptms
        WHERE ptm = :mid
        RETURNING ptm AS ptm
    '''
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params={"mid": str(mid)})
    return df.iloc[0].to_dict() if not df.empty else None
    
def insert_drug(drug: str):
    sql = '''
        INSERT INTO drugs(drug)
        VALUES (:n)
        RETURNING drug AS drug
    '''
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params={"n": drug})
    return df.iloc[0].to_dict() if not df.empty else None

def update_drug(current: str, new: str):
    sql = '''
        UPDATE drugs
        SET drug = :n
        WHERE drug = :c
        RETURNING drug AS drug
    '''
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params={"c": current, "n": new})
    return df.iloc[0].to_dict() if not df.empty else None
    
def delete_drug(mid: str):
    sql = '''
        DELETE FROM drugs
        WHERE drug = :mid
        RETURNING drug AS drug
    '''
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params={"mid": str(mid)})
    return df.iloc[0].to_dict() if not df.empty else None

def update_spearman(row: int, val: float):
    sql = '''
        UPDATE ptm_correlation_matrix
        SET spearman_score = :v
        WHERE id = :r
        RETURNING spearman_score AS spearman_score
    '''
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params={"r": row, "v": val})
    return df.iloc[0].to_dict() if not df.empty else None
    
# --------------- UI ---------------
st.title("👻 PTMsToPathways DB Viewer")
st.caption("Neon-ready: SSL on, statement_timeout set after connect, and fast-fail timeouts.")

with st.sidebar:
    row_limit = st.number_input("Row limit", min_value=1, max_value=2000, value=200, step=50)

tab1, tab2, tab3 = st.tabs(["🏚️ Input", "🏚️ Dataset", "🏚️ Correlation Matrix"])
with tab1:
    
    # Display ptms
    st.subheader("Input data")
    sql = "SELECT ptm FROM ptms ORDER BY ptm"
    st.dataframe(fetch_df(sql, {"lim": int(row_limit)}), use_container_width=True)
    
    # Insert a ptm
    st.markdown("### ➕ Insert PTM")
    with st.form("insert_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            ptm = st.text_input("ptm*", placeholder="AARS ubi k474")
        if st.form_submit_button("Insert"):
            if not ptm.strip():
                st.warning("Cannot have a PTM name be empty!")        
            else:
                rec = insert_ptm(ptm.strip())
                if rec:
                    st.session_state.just_inserted = rec
                    st.rerun()
    
    ptms = fetch_df('SELECT ptm FROM ptms')
           
    # Update a ptm
    st.markdown("### ✏️ Update")
    if ptms.empty:
        st.caption("Nothing to update.")
    else:
        ptm_choices = {str(r.ptm): f"{str(r.ptm)}" for _, r in ptms.iterrows()}
        sel_id = st.selectbox("ptm", options=list(ptm_choices.keys()), format_func=lambda k: ptm_choices[k], key="upd_sel")
        current = ptms[ptms["ptm"] == sel_id].iloc[0]

        with st.form("update_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("ptm", current["ptm"])
                
            if st.form_submit_button("Update"):
                rec = update_ptm(str(current["ptm"]), str(new_name))
                if rec:
                    st.session_state.just_updated = rec
                    st.rerun()
     
    # Delete a ptm
    st.markdown("### 🗑️ Delete")
    if ptms.empty:
        st.caption("Nothing to delete.")
    else:
        ptm_choices = {str(r.ptm): f"{str(r.ptm)}" for _, r in ptms.iterrows()}
        colA, colB = st.columns([3, 2])
        with colA:
            del_id = st.selectbox("Select ptm", options=list(ptm_choices.keys()),
                                  format_func=lambda k: ptm_choices[k], key="del_sel")
        with colB:
            confirm = st.checkbox("Confirm deletion", key="del_confirm")

        if st.button("Delete selected"):
            if not confirm:
                st.warning("Please confirm before deleting.")
            else:
                rec = delete_ptm(str(del_id))
                if rec:
                    st.session_state.just_deleted = rec
                    st.rerun()


    
    # Display drugs
    sql2 = "SELECT drug FROM drugs ORDER BY drug"
    st.dataframe(fetch_df(sql2, {"lim": int(row_limit)}), use_container_width=True)
    
    # Insert a drug
    st.markdown("### ➕ Insert DRUG")
    with st.form("insert_form2", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            drug = st.text_input("drug*", placeholder="H3122SEPTM_pTyr.PR2")
        if st.form_submit_button("Insert"):
            if not ptm.strip():
                st.warning("Cannot have a drug name be empty!")        
            else:
                rec = insert_drug(drug.strip())
                if rec:
                    st.session_state.just_inserted = rec
                    st.rerun()
    
    drugs = fetch_df('SELECT drug FROM drugs')
    
    # Update a ptm
    st.markdown("### ✏️ Update")
    if drugs.empty:
        st.caption("Nothing to update.")
    else:
        drug_choices = {str(r.drug): f"{str(r.drug)}" for _, r in drugs.iterrows()}
        sel_id = st.selectbox("drug", options=list(drug_choices.keys()), format_func=lambda k: drug_choices[k], key="upd_sel2")
        current = drugs[drugs["drug"] == sel_id].iloc[0]

        with st.form("update_form2", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("drug", current["drug"])
                
            if st.form_submit_button("Update"):
                rec = update_drug(str(current["drug"]), str(new_name))
                if rec:
                    st.session_state.just_updated = rec
                    st.rerun()
    
    # Delete a drug
    st.markdown("### 🗑️ Delete")
    if drugs.empty:
        st.caption("Nothing to delete.")
    else:
        drug_choices = {str(r.drug): f"{str(r.drug)})" for _, r in drugs.iterrows()}
        colA, colB = st.columns([3, 2])
        with colA:
            del_id = st.selectbox("Select drug", options=list(drug_choices.keys()),
                                  format_func=lambda k: drug_choices[k], key="del_sel2")
        with colB:
            confirm = st.checkbox("Confirm deletion", key="del_confirm2")

        if st.button("Delete selected", key="del_drug"):
            if not confirm:
                st.warning("Please confirm before deleting.")
            else:
                rec = delete_drug(str(del_id))
                if rec:
                    st.session_state.just_deleted = rec
                    st.rerun()

    
with tab2:
    st.subheader("ptmdataset")
    
    # Fetch ptms and drugs
    ptms = fetch_df('SELECT DISTINCT ptm FROM ptms;') # I love sql used like this
    drugs = fetch_df('SELECT DISTINCT drug FROM drugs;')
    
    ptms['key'] = 0 # Required for the cross join 
    drugs['key'] = 0
    ptmdataset = pd.merge(ptms, drugs, on='key') # Perform a cross join
    
    # Randomize the reaction score between every ptm and drug pair
    reaction_score = list()
    for r in range(0, len(ptmdataset)):
        reaction_score.append(random.uniform(0,10))
    
    ptmdataset['reaction_score'] = reaction_score
    
    # THE BEST LINE OF CODE EVER WRITTEN - just transforms the data frame into psql database
    with engine.connect() as conn:
       ptmdataset.to_sql('ptmdataset', conn, if_exists='replace')
    
    
    sql = '''SELECT ptm, drug, reaction_score FROM ptmdataset;'''
    st.dataframe(fetch_df(sql, {"lim": int(row_limit)}), use_container_width=True)
    
with tab3:
    st.subheader("correlation matrix")
    
    PTMdataset = fetch_df('''SELECT DISTINCT ptm FROM PTMdataset''')
    reaction_score = fetch_df("SELECT ptm, SUM(reaction_score) FROM PTMdataset GROUP BY ptm") # Holds reaction scores
    
    ptm1 = list()
    ptm2 = list()
    spearman_score = list()
    
    for i in range(0, len(reaction_score)): # For loop for creating the spearman score values
        for j in range(0, len(reaction_score)):
            p1 = reaction_score.iloc[i, 0]
            p2 = reaction_score.iloc[j, 0]
            
            s1 = float(reaction_score.iloc[i, 1])
            s2 = float(reaction_score.iloc[j, 1])
            
            ptm1.append(p1)
            ptm2.append(p2)
            spearman_score.append(min(s1, s2) / max(s1, s2))
    
    data = {'ptm1':ptm1, 'ptm2':ptm2,'spearman_score':spearman_score} # Add them all to a new data frame
    ptm_correlation_matrix = pd.DataFrame(data) 
    
    # The best line of code ever written: Basically overwrites the database on the psql server
    with engine.connect() as conn:
       ptm_correlation_matrix.to_sql('ptm_correlation_matrix', conn, if_exists='replace') 
       
    sql = '''SELECT ptm1, ptm2, spearman_score FROM ptm_correlation_matrix;'''
    st.dataframe(fetch_df(sql, {"lim": int(row_limit)}), use_container_width=True)


st.markdown("---")
st.caption(f"Connecting to {PGHOST}:{PGPORT}/{PGDATABASE} as {PGUSER} (sslmode={PGSSLMODE}).")
