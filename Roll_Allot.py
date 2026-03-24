import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🎯 Centre Allotment System (Day + Session Based)")

# -------------------------------
# FILE UPLOADS
# -------------------------------
lab_file = st.file_uploader("Upload Lab Details", type=["csv", "xlsx"])
centre_file = st.file_uploader("Upload Centre Details", type=["csv", "xlsx"])
pref_file = st.file_uploader("Upload Preferences", type=["csv", "xlsx"])
cand_file = st.file_uploader("Upload Candidates", type=["csv", "xlsx"])
reg_file = st.file_uploader("Upload Registrations", type=["csv", "xlsx"])


# -------------------------------
# LOAD FILE
# -------------------------------
def load_file(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    df.columns = df.columns.str.strip().str.lower()
    return df


# -------------------------------
# VALIDATION
# -------------------------------
def validate_columns(df, required_cols, name):
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"❌ Missing columns in {name}: {missing}")
        st.write("Available:", df.columns.tolist())
        st.stop()


# -------------------------------
# MAIN
# -------------------------------
if st.button("Run Allotment"):

    if not all([lab_file, centre_file, pref_file, cand_file, reg_file]):
        st.error("⚠️ Upload all files")
        st.stop()

    with st.spinner("Processing..."):

        labs = load_file(lab_file)
        centres = load_file(centre_file)
        prefs = load_file(pref_file)
        candidates = load_file(cand_file)
        registrations = load_file(reg_file)

        # -------------------------------
        # VALIDATION
        # -------------------------------
        validate_columns(labs, ['collegecode', 'venueno', 'labname', 'noofsys'], "Lab")
        validate_columns(centres, ['centrecode', 'centrename'], "Centre")
        validate_columns(prefs, ['applno'], "Prefs")
        validate_columns(candidates, ['applno', 'name', 'eng', 'bpharm'], "Candidates")
        validate_columns(registrations, ['applno', 'paymentmode'], "Registrations")

        # -------------------------------
        # CENTRE LOOKUP
        # -------------------------------
        centre_lookup = dict(zip(centres['centrecode'], centres['centrename']))

        # -------------------------------
        # CAPACITY
        # -------------------------------
        capacity = {}
        centre_name = {}
        venue_map = {}
        lab_map = {}

        for _, row in labs.iterrows():
            code = row['collegecode']

            capacity[code] = capacity.get(code, 0) + int(row['noofsys'])
            centre_name[code] = centre_lookup.get(code, f"UNKNOWN-{code}")

            venue_map.setdefault(code, []).append(row['venueno'])
            lab_map.setdefault(code, []).append(row['labname'])

        # 10% buffer
        for k in capacity:
            capacity[k] = int(capacity[k] * 0.90)

        # -------------------------------
        # SLOT CAPACITY (NEW)
        # -------------------------------
        ENG_DAYS = [1, 2, 3, 4, 5, 6]
        BPHARM_DAYS = [1, 2]

        slot_capacity = {}

        for centre, cap in capacity.items():
            slot_capacity[centre] = {}

            # ENG → 6 days afternoon
            for d in ENG_DAYS:
                slot_capacity[centre][(d, "AFTERNOON", "ENG")] = cap

            # BPHARM → 2 days morning
            for d in BPHARM_DAYS:
                slot_capacity[centre][(d, "MORNING", "BPHARM")] = cap

        # -------------------------------
        # PREFERENCES
        # -------------------------------
        pref_map = {}

        for _, row in prefs.iterrows():
            pref = []
            for i in range(1, 16):
                col = f'centre{i}'
                if col in row and pd.notna(row[col]):
                    pref.append(row[col])
            pref_map[row['applno']] = pref

        # -------------------------------
        # FILTER
        # -------------------------------
        valid_reg = registrations[
            registrations['paymentmode'].isin(['O', 'F'])
        ]

        merged = candidates.merge(
            valid_reg,
            on="applno",
            suffixes=('', '_reg')
        )

        merged = merged[
            (merged['eng'] == 'Y') | (merged['bpharm'] == 'Y')
        ]

        merged = merged.sort_values("applno")

        # -------------------------------
        # ALLOTMENT
        # -------------------------------
        results = []

        for _, cand in merged.iterrows():

            applno = cand['applno']

            pref_centre = "-"
            allotted = "NOT ALLOTTED"
            allotted_name = "-"
            venue = "-"
            lab = "-"
            day = "-"
            session = "-"

            # exam type
            if cand['eng'] == 'Y' and cand['bpharm'] == 'Y':
                exam_types = ["ENG", "BPHARM"]
            elif cand['eng'] == 'Y':
                exam_types = ["ENG"]
            else:
                exam_types = ["BPHARM"]

            if applno in pref_map:

                pref_list = pref_map[applno]

                if len(pref_list) > 0:
                    pref_centre = pref_list[0]

                for centre in pref_list:

                    if centre not in slot_capacity:
                        continue

                    allocated = False

                    for exam in exam_types:

                        if exam == "ENG":
                            days = ENG_DAYS
                            session_type = "AFTERNOON"
                        else:
                            days = BPHARM_DAYS
                            session_type = "MORNING"

                        for d in days:

                            key = (d, session_type, exam)

                            if slot_capacity[centre].get(key, 0) > 0:

                                allotted = centre
                                allotted_name = centre_name.get(centre, "-")

                                venue = venue_map.get(centre, ["-"])[0]
                                lab = lab_map.get(centre, ["-"])[0]

                                day = d
                                session = session_type

                                slot_capacity[centre][key] -= 1
                                allocated = True
                                break

                        if allocated:
                            break

                    if allocated:
                        break

            results.append({
                "ApplNo": applno,
                "Name": cand['name'],
                "Exam": "+".join(exam_types),
                "Pref": pref_centre,
                "Allotted": allotted,
                "Centre Name": allotted_name,
                "Venue": venue,
                "Lab": lab,
                "Day": day,
                "Session": session
            })

        df = pd.DataFrame(results)

    # -------------------------------
    # OUTPUT
    # -------------------------------
    st.success("✅ Allotment Completed")

    st.dataframe(df, use_container_width=True)

    st.subheader("📊 Summary")
    st.write(df['Allotted'].value_counts())

    # Download
    csv = df.to_csv(index=False).encode('utf-8')

    st.download_button(
        "⬇ Download Result CSV",
        csv,
        "centre_allotment.csv",
        "text/csv"
    )
