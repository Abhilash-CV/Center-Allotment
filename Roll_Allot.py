import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🎯 Centre Allotment System (Stable Version)")

# -------------------------------
# FILE UPLOADS
# -------------------------------
lab_file = st.file_uploader("Lab Details", type=["csv","xlsx"])
centre_file = st.file_uploader("Centre Details", type=["csv","xlsx"])
pref_file = st.file_uploader("Preferences", type=["csv","xlsx"])
cand_file = st.file_uploader("Candidates", type=["csv","xlsx"])
reg_file = st.file_uploader("Registrations", type=["csv","xlsx"])


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
    centres = load(centre_file)
    prefs = load(pref_file)
    candidates = load(cand_file)
    reg = load(reg_file)

    # -------------------------------
    # NORMALIZE TYPES
    # -------------------------------
    labs['collegecode'] = labs['collegecode'].astype(str)
    centres['centrecode'] = centres['centrecode'].astype(str)

    # -------------------------------
    # FILTER
    # -------------------------------
    valid = reg[reg['paymentmode'].isin(['O','F'])]
    merged = candidates.merge(valid, on="applno", suffixes=('','_r'))
    merged = merged[(merged['eng']=='Y') | (merged['bpharm']=='Y')]
    merged = merged.sort_values("applno")

    # -------------------------------
    # LOOKUPS
    # -------------------------------
    centre_lookup = dict(zip(centres['centrecode'], centres['centrename']))

    # -------------------------------
    # CAPACITY
    # -------------------------------
    capacity = {}
    for _, r in labs.iterrows():
        c = str(r['collegecode'])
        capacity[c] = capacity.get(c, 0) + int(r['noofsys'])

    for k in capacity:
        capacity[k] = int(capacity[k] * 0.9)

    # -------------------------------
    # SLOT CAPACITY
    # -------------------------------
    slot = {}
    for c, cap in capacity.items():
        slot[c] = {}

        for d in [1,2,3,4,5,6]:
            slot[c][(d,"AFTERNOON","ENG")] = cap

        for d in [1,2]:
            slot[c][(d,"MORNING","BPHARM")] = cap

    # -------------------------------
    # PREFERENCES
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
        name = cand['name']

        pref_list = pref_map.get(applno, [])
        pref_list = [str(x) for x in pref_list]

        pref_centre = pref_list[0] if pref_list else "-"

        allocated = False

        for centre in pref_list:

            if centre not in slot:
                continue

            centre_name = centre_lookup.get(centre, "-")

            # -------------------
            # ENG + BPHARM
            # -------------------
            if cand['eng']=='Y' and cand['bpharm']=='Y':

                # try same day
                for d in [1,2]:
                    if (slot[centre][(d,"MORNING","BPHARM")] > 0 and
                        slot[centre][(d,"AFTERNOON","ENG")] > 0):

                        slot[centre][(d,"MORNING","BPHARM")] -= 1
                        slot[centre][(d,"AFTERNOON","ENG")] -= 1

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

                        allocated = True
                        break

                if allocated:
                    break

                # fallback
                for d in [1,2]:
                    if slot[centre][(d,"MORNING","BPHARM")] > 0:
                        slot[centre][(d,"MORNING","BPHARM")] -= 1

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
                        allocated = True
                        break

                for d in [1,2,3,4,5,6]:
                    if slot[centre][(d,"AFTERNOON","ENG")] > 0:
                        slot[centre][(d,"AFTERNOON","ENG")] -= 1

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
                        allocated = True
                        break

                if allocated:
                    break

            # -------------------
            # ENG ONLY
            # -------------------
            elif cand['eng']=='Y':

                for d in [1,2,3,4,5,6]:
                    if slot[centre][(d,"AFTERNOON","ENG")] > 0:
                        slot[centre][(d,"AFTERNOON","ENG")] -= 1

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

                        allocated = True
                        break

                if allocated:
                    break

            # -------------------
            # BPHARM ONLY
            # -------------------
            else:

                for d in [1,2]:
                    if slot[centre][(d,"MORNING","BPHARM")] > 0:
                        slot[centre][(d,"MORNING","BPHARM")] -= 1

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

                        allocated = True
                        break

                if allocated:
                    break

        if not allocated:
            not_allotted += 1

    df = pd.DataFrame(results)

    # -------------------------------
    # OUTPUT + DEBUG
    # -------------------------------
    st.success("✅ Completed")

    st.write("Total Candidates:", len(merged))
    st.write("Total Allocations (rows):", len(df))
    st.write("Not Allotted:", not_allotted)

    st.dataframe(df, use_container_width=True)

    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode(),
        "allotment.csv"
    )
