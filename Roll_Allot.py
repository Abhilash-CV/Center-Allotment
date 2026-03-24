import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🎯 Centre Allotment System (Fully Corrected)")

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
    centre_district = dict(zip(centres['centrecode'], centres['centredistrict']))

    # -------------------------------
    # CAPACITY
    # -------------------------------
    capacity = {}
    venue_map = {}
    lab_map = {}

    for _, r in labs.iterrows():
        c = str(r['collegecode'])
        capacity[c] = capacity.get(c, 0) + int(r['noofsys'])
        venue_map.setdefault(c, []).append(r['venueno'])
        lab_map.setdefault(c, []).append(r['labname'])

    # 90% rule
    for k in capacity:
        capacity[k] = int(capacity[k] * 0.9)

    # -------------------------------
    # SLOT CAPACITY
    # -------------------------------
    ENG_DAYS = [1,2,3,4,5,6]
    BPHARM_DAYS = [1,2]

    slot = {}
    usage = {}

    for c, cap in capacity.items():
        slot[c] = {}
        usage[c] = {}

        for d in ENG_DAYS:
            slot[c][(d,"AFTERNOON","ENG")] = cap
            usage[c][(d,"AFTERNOON")] = 0

        for d in BPHARM_DAYS:
            slot[c][(d,"MORNING","BPHARM")] = cap
            usage[c][(d,"MORNING")] = 0

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

    for _, cand in merged.iterrows():

        applno = cand['applno']
        name = cand['name']
        district = cand.get('cdistrict', "")

        if applno not in pref_map:
            continue

        pref_list = pref_map[applno]
        pref_centre = pref_list[0] if pref_list else "-"

        # district priority
        pref_list = sorted(
            pref_list,
            key=lambda x: 0 if centre_district.get(str(x)) == district else 1
        )

        allocated = False

        for centre in pref_list:

            centre = str(centre)

            if centre not in slot:
                continue

            centre_name = centre_lookup.get(centre,"-")

            # -------------------
            # DUAL FIXED
            # -------------------
            if cand['eng']=='Y' and cand['bpharm']=='Y':

                # Try SAME DAY
                for d in BPHARM_DAYS:
                    k1 = (d,"MORNING","BPHARM")
                    k2 = (d,"AFTERNOON","ENG")

                    if slot[centre][k1]>0 and slot[centre][k2]>0:

                        slot[centre][k1]-=1
                        slot[centre][k2]-=1

                        v = venue_map[centre][0]
                        l = lab_map[centre][0]

                        results.append({
                            "ApplNo": applno,
                            "Name": name,
                            "Preferred Centre": pref_centre,
                            "Allotted Centre": centre,
                            "CollegeCode": centre,
                            "Centre Name": centre_name,
                            "Exam": "BPHARM",
                            "Day": d,
                            "Session": "MORNING",
                            "Venue": v,
                            "Lab": l
                        })

                        results.append({
                            "ApplNo": applno,
                            "Name": name,
                            "Preferred Centre": pref_centre,
                            "Allotted Centre": centre,
                            "CollegeCode": centre,
                            "Centre Name": centre_name,
                            "Exam": "ENG",
                            "Day": d,
                            "Session": "AFTERNOON",
                            "Venue": v,
                            "Lab": l
                        })

                        allocated = True
                        break

                # If not possible → allocate separately
                if not allocated:

                    # BPHARM
                    for d in BPHARM_DAYS:
                        k = (d,"MORNING","BPHARM")
                        if slot[centre][k]>0:
                            slot[centre][k]-=1

                            results.append({
                                "ApplNo": applno,
                                "Name": name,
                                "Preferred Centre": pref_centre,
                                "Allotted Centre": centre,
                                "CollegeCode": centre,
                                "Centre Name": centre_name,
                                "Exam": "BPHARM",
                                "Day": d,
                                "Session": "MORNING",
                                "Venue": venue_map[centre][0],
                                "Lab": lab_map[centre][0]
                            })
                            break

                    # ENG
                    for d in ENG_DAYS:
                        k = (d,"AFTERNOON","ENG")
                        if slot[centre][k]>0:
                            slot[centre][k]-=1

                            results.append({
                                "ApplNo": applno,
                                "Name": name,
                                "Preferred Centre": pref_centre,
                                "Allotted Centre": centre,
                                "CollegeCode": centre,
                                "Centre Name": centre_name,
                                "Exam": "ENG",
                                "Day": d,
                                "Session": "AFTERNOON",
                                "Venue": venue_map[centre][0],
                                "Lab": lab_map[centre][0]
                            })
                            break

                    allocated = True

            # -------------------
            # ENG ONLY
            # -------------------
            elif cand['eng']=='Y':

                for d in ENG_DAYS:
                    k = (d,"AFTERNOON","ENG")
                    if slot[centre][k]>0:
                        slot[centre][k]-=1

                        results.append({
                            "ApplNo": applno,
                            "Name": name,
                            "Preferred Centre": pref_centre,
                            "Allotted Centre": centre,
                            "CollegeCode": centre,
                            "Centre Name": centre_name,
                            "Exam": "ENG",
                            "Day": d,
                            "Session": "AFTERNOON",
                            "Venue": venue_map[centre][0],
                            "Lab": lab_map[centre][0]
                        })
                        allocated = True
                        break

            # -------------------
            # BPHARM ONLY
            # -------------------
            else:

                for d in BPHARM_DAYS:
                    k = (d,"MORNING","BPHARM")
                    if slot[centre][k]>0:
                        slot[centre][k]-=1

                        results.append({
                            "ApplNo": applno,
                            "Name": name,
                            "Preferred Centre": pref_centre,
                            "Allotted Centre": centre,
                            "CollegeCode": centre,
                            "Centre Name": centre_name,
                            "Exam": "BPHARM",
                            "Day": d,
                            "Session": "MORNING",
                            "Venue": venue_map[centre][0],
                            "Lab": lab_map[centre][0]
                        })
                        allocated = True
                        break

            if allocated:
                break

    df = pd.DataFrame(results)

    # -------------------------------
    # OUTPUT
    # -------------------------------
    st.success("✅ Allotment Completed")
    st.dataframe(df, use_container_width=True)

    st.subheader("📊 Centre Utilization")
    st.write(df['Allotted Centre'].value_counts())

    st.subheader("📅 Day-wise Load")
    st.write(df['Day'].value_counts().sort_index())

    st.subheader("🕒 Session Distribution")
    st.write(df['Session'].value_counts())

    st.download_button(
        "⬇ Download CSV",
        df.to_csv(index=False).encode(),
        "centre_allotment.csv"
    )
