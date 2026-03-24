import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🎯 Centre Allotment System (Final Fix)")

# Uploads
lab_file = st.file_uploader("Lab Details", type=["csv","xlsx"])
centre_file = st.file_uploader("Centre Details", type=["csv","xlsx"])
pref_file = st.file_uploader("Preferences", type=["csv","xlsx"])
cand_file = st.file_uploader("Candidates", type=["csv","xlsx"])
reg_file = st.file_uploader("Registrations", type=["csv","xlsx"])


def load(file):
    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
    df.columns = df.columns.str.strip().str.lower()
    return df


if st.button("Run Allotment"):

    labs = load(lab_file)
    prefs = load(pref_file)
    candidates = load(cand_file)
    reg = load(reg_file)

    # Normalize
    labs['collegecode'] = labs['collegecode'].astype(str)

    # Filter
    valid = reg[reg['paymentmode'].isin(['O','F'])]
    merged = candidates.merge(valid, on="applno")
    merged = merged[(merged['eng']=='Y') | (merged['bpharm']=='Y')]

    # Capacity
    capacity = {}

    for _, r in labs.iterrows():
        c = str(r['collegecode'])
        capacity[c] = capacity.get(c,0) + int(r['noofsys'])

    for k in capacity:
        capacity[k] = int(capacity[k] * 0.9)

    # Slot
    slot = {}

    for c, cap in capacity.items():
        slot[c] = {}

        for d in range(1,7):
            slot[c][(d,"AFTERNOON","ENG")] = cap

        for d in [1,2]:
            slot[c][(d,"MORNING","BPHARM")] = cap

    # Preferences
    pref_map = {}

    for _, r in prefs.iterrows():
        pref = []
        for i in range(1,16):
            col = f'centre{i}'
            if col in r and pd.notna(r[col]):
                pref.append(str(r[col]))
        pref_map[r['applno']] = pref

    # -------------------------------
    # ALLOTMENT (FINAL FIX)
    # -------------------------------
    results = []
    not_allotted = 0

    for _, cand in merged.iterrows():

        applno = cand['applno']
        name = cand['name']

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

    # Output
    st.success("✅ Completed")

    st.write("Total Candidates:", len(merged))
    st.write("Allocated Rows:", len(df))
    st.write("Not Allotted:", not_allotted)

    st.dataframe(df)

    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode(),
        "allotment.csv"
    )
