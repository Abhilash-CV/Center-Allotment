import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🎯 Centre Allotment System (Correct Mapping Fixed)")

# -------------------------------
# FILES
# -------------------------------
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
    centres = load(centre_file)
    prefs = load(pref_file)
    candidates = load(cand_file)
    reg = load(reg_file)

    # -------------------------------
    # NORMALIZE
    # -------------------------------
    labs['collegecode'] = labs['collegecode'].astype(str)
    centres['centrecode'] = centres['centrecode'].astype(str)

    # -------------------------------
    # 🔥 BUILD CENTRE → COLLEGE MAP
    # -------------------------------

    centre_to_colleges = {}

    # CASE 1: if lab has centrecode
    if 'centrecode' in labs.columns:

        for _, r in labs.iterrows():
            centre = str(r['centrecode'])
            college = str(r['collegecode'])

            centre_to_colleges.setdefault(centre, []).append(college)

    else:
        # CASE 2: fallback via district
        st.warning("⚠️ centrecode not in lab → using district mapping")

        # centre → district
        centre_district = dict(zip(
            centres['centrecode'],
            centres['centredistrict']
        ))

        # lab must have district
        if 'district' not in labs.columns and 'centredistrict' not in labs.columns:
            st.error("❌ Cannot map centre → college. Need centrecode or district.")
            st.stop()

        lab_district_col = 'district' if 'district' in labs.columns else 'centredistrict'

        for _, c_row in centres.iterrows():
            centre = str(c_row['centrecode'])
            c_dist = c_row['centredistrict']

            matched_colleges = labs[
                labs[lab_district_col] == c_dist
            ]['collegecode'].astype(str).tolist()

            centre_to_colleges[centre] = matched_colleges

    st.write("Sample mapping:", list(centre_to_colleges.items())[:3])

    # -------------------------------
    # CAPACITY (per college)
    # -------------------------------
    capacity = {}

    for _, r in labs.iterrows():
        college = str(r['collegecode'])
        capacity[college] = capacity.get(college, 0) + int(r['noofsys'])

    for k in capacity:
        capacity[k] = int(capacity[k] * 0.9)

    # -------------------------------
    # SLOT
    # -------------------------------
    slot = {}

    for college, cap in capacity.items():
        slot[college] = {}

        for d in range(1,7):
            slot[college][(d,"AFTERNOON","ENG")] = cap

        for d in [1,2]:
            slot[college][(d,"MORNING","BPHARM")] = cap

    # -------------------------------
    # PREF MAP
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
    # FILTER
    # -------------------------------
    valid = reg[reg['paymentmode'].isin(['O','F'])]

    merged = candidates.merge(valid, on="applno")
    merged = merged[(merged['eng']=='Y') | (merged['bpharm']=='Y')]

    # -------------------------------
    # ALLOTMENT
    # -------------------------------
    results = []
    not_allotted = 0

    for _, cand in merged.iterrows():

        applno = cand['applno']
        name = cand['name']

        pref_list = pref_map.get(applno, [])
        pref_centre = pref_list[0] if pref_list else "-"

        allocated = False

        for centre in pref_list:

            colleges = centre_to_colleges.get(centre, [])

            for college in colleges:

                if college not in slot:
                    continue

                # ENG
                if cand['eng']=='Y':
                    for d in range(1,7):
                        k = (d,"AFTERNOON","ENG")
                        if slot[college][k] > 0:

                            slot[college][k] -= 1

                            results.append({
                                "ApplNo": applno,
                                "Name": name,
                                "Preferred Centre": pref_centre,
                                "Allotted Centre": centre,
                                "CollegeCode": college,
                                "Exam": "ENG",
                                "Day": d,
                                "Session": "AFTERNOON"
                            })

                            allocated = True
                            break

                # BPHARM
                if cand['bpharm']=='Y':
                    for d in [1,2]:
                        k = (d,"MORNING","BPHARM")
                        if slot[college][k] > 0:

                            slot[college][k] -= 1

                            results.append({
                                "ApplNo": applno,
                                "Name": name,
                                "Preferred Centre": pref_centre,
                                "Allotted Centre": centre,
                                "CollegeCode": college,
                                "Exam": "BPHARM",
                                "Day": d,
                                "Session": "MORNING"
                            })

                            allocated = True
                            break

                if allocated:
                    break

            if allocated:
                break

        if not allocated:
            not_allotted += 1

    df = pd.DataFrame(results)

    # -------------------------------
    # OUTPUT
    # -------------------------------
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
