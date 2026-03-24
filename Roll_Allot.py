import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🎯 Centre Allotment System (Final Stable Version)")

# -------------------------------
# FILE UPLOADS
# -------------------------------
lab_file = st.file_uploader("Lab Details", type=["csv","xlsx"])
centre_file = st.file_uploader("Centre Details", type=["csv","xlsx"])
pref_file = st.file_uploader("Preferences", type=["csv","xlsx"])
cand_file = st.file_uploader("Candidates", type=["csv","xlsx"])
reg_file = st.file_uploader("Registrations", type=["csv","xlsx"])


# -------------------------------
# LOAD FUNCTION
# -------------------------------
def load(file):
    if file is None:
        st.error("❌ Missing file")
        st.stop()

    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
    df.columns = df.columns.str.strip().str.lower()
    return df


# -------------------------------
# RUN
# -------------------------------
if st.button("Run Allotment"):

    if not all([lab_file, centre_file, pref_file, cand_file, reg_file]):
        st.error("⚠️ Upload all files")
        st.stop()

    labs = load(lab_file)
    prefs = load(pref_file)
    candidates = load(cand_file)
    reg = load(reg_file)

    # -------------------------------
    # NORMALIZE
    # -------------------------------
    labs['collegecode'] = labs['collegecode'].astype(str)

    # -------------------------------
    # FILTER VALID CANDIDATES
    # -------------------------------
    valid = reg[reg['paymentmode'].isin(['O','F'])]

    # ✅ FIXED MERGE (NO name_x issue)
    merged = candidates.merge(
        valid,
        on="applno",
        suffixes=('', '_reg')
    )

    merged = merged[
        (merged['eng']=='Y') | (merged['bpharm']=='Y')
    ]

    merged = merged.sort_values("applno")

    # -------------------------------
    # BUILD CAPACITY
    # -------------------------------
    capacity = {}

    for _, r in labs.iterrows():
        c = str(r['collegecode'])
        capacity[c] = capacity.get(c, 0) + int(r['noofsys'])

    # Apply 10% buffer
    for k in capacity:
        capacity[k] = int(capacity[k] * 0.9)

    # -------------------------------
    # SLOT CAPACITY
    # -------------------------------
    slot = {}

    for c, cap in capacity.items():
        slot[c] = {}

        # ENG → 6 days afternoon
        for d in range(1,7):
            slot[c][(d,"AFTERNOON","ENG")] = cap

        # BPHARM → 2 days morning
        for d in [1,2]:
            slot[c][(d,"MORNING","BPHARM")] = cap

    # -------------------------------
    # PREFERENCE MAP
    # -------------------------------
    pref_map = {}

    for _, r in prefs.iterrows():
        pref = []
        for i in range(1,16):
            col = f'centre{i}'
            if col in r and pd.notna(r[col]):
                pref.append(str(r[col]))
        pref_map[r['applno']] = pref

    # -------------------------------
    # ALLOTMENT
    # -------------------------------
    results = []
    not_allotted = 0

    for _, cand in merged.iterrows():

        applno = cand['applno']
        name = cand['name']   # ✅ FIXED

        pref_list = pref_map.get(applno, [])
        pref_centre = pref_list[0] if pref_list else "-"

        allocated_any = False

        # -------------------
        # BPHARM FIRST
        # -------------------
        if cand['bpharm'] == 'Y':

            for centre in pref_list:

                if centre not in slot:
                    continue

                for d in [1,2]:
                    k = (d,"MORNING","BPHARM")

                    if slot[centre][k] > 0:

                        slot[centre][k] -= 1

                        results.append({
                            "ApplNo": applno,
                            "Name": name,
                            "Preferred Centre": pref_centre,
                            "Allotted Centre": centre,
                            "CollegeCode": centre,
                            "Exam": "BPHARM",
                            "Day": d,
                            "Session": "MORNING"
                        })

                        allocated_any = True
                        break

                if allocated_any:
                    break

        # -------------------
        # ENG NEXT
        # -------------------
        if cand['eng'] == 'Y':

            allocated_eng = False

            for centre in pref_list:

                if centre not in slot:
                    continue

                for d in range(1,7):
                    k = (d,"AFTERNOON","ENG")

                    if slot[centre][k] > 0:

                        slot[centre][k] -= 1

                        results.append({
                            "ApplNo": applno,
                            "Name": name,
                            "Preferred Centre": pref_centre,
                            "Allotted Centre": centre,
                            "CollegeCode": centre,
                            "Exam": "ENG",
                            "Day": d,
                            "Session": "AFTERNOON"
                        })

                        allocated_eng = True
                        break

                if allocated_eng:
                    break

            if allocated_eng:
                allocated_any = True

        if not allocated_any:
            not_allotted += 1

    df = pd.DataFrame(results)

    # -------------------------------
    # OUTPUT
    # -------------------------------
    st.success("✅ Allotment Completed")

    st.write("Total Candidates:", len(merged))
    st.write("Allocated Rows:", len(df))
    st.write("Not Allotted:", not_allotted)

    st.dataframe(df, use_container_width=True)

    st.download_button(
        "⬇ Download CSV",
        df.to_csv(index=False).encode(),
        "centre_allotment.csv"
    )
