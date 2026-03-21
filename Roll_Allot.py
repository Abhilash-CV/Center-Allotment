import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🎯 Centre Allotment System (CSV / Excel)")

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

    # Normalize column names
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
# MAIN PROCESS
# -------------------------------
if st.button("Run Allotment"):

    if not all([lab_file, centre_file, pref_file, cand_file, reg_file]):
        st.error("⚠️ Please upload all required files")
        st.stop()

    with st.spinner("Processing..."):

        # Load all files
        labs = load_file(lab_file)
        centres = load_file(centre_file)
        prefs = load_file(pref_file)
        candidates = load_file(cand_file)
        registrations = load_file(reg_file)

        # -------------------------------
        # DEBUG VIEW
        # -------------------------------
        with st.expander("🔍 Debug Columns"):
            st.write("Lab:", labs.columns.tolist())
            st.write("Centre:", centres.columns.tolist())
            st.write("Prefs:", prefs.columns.tolist())
            st.write("Candidates:", candidates.columns.tolist())
            st.write("Registrations:", registrations.columns.tolist())

        # -------------------------------
        # VALIDATE STRUCTURE
        # -------------------------------
        validate_columns(labs, ['collegecode', 'venueno', 'labname', 'noofsys'], "Lab")
        validate_columns(centres, ['centrecode', 'centrename'], "Centre")
        validate_columns(prefs, ['applno'], "Preferences")
        validate_columns(candidates, ['applno', 'name', 'eng', 'bpharm'], "Candidates")
        validate_columns(registrations, ['applno', 'paymentmode'], "Registrations")

        # -------------------------------
        # CENTRE LOOKUP (JOIN)
        # -------------------------------
        centre_lookup = dict(zip(
            centres['centrecode'],
            centres['centrename']
        ))

        # -------------------------------
        # CAPACITY BUILD
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

        # Apply 10% buffer
        for k in capacity:
            capacity[k] = int(capacity[k] * 0.90)

        # -------------------------------
        # PREFERENCE MAP
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
        # FILTER VALID CANDIDATES
        # -------------------------------
        valid_reg = registrations[
            registrations['paymentmode'].isin(['O', 'F'])
        ]

        # ✅ FIXED MERGE (NO name_x issue)
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

            if applno in pref_map:
                pref_list = pref_map[applno]

                if len(pref_list) > 0:
                    pref_centre = pref_list[0]

                for centre in pref_list:
                    if centre in capacity and capacity[centre] > 0:

                        allotted = centre
                        allotted_name = centre_name.get(centre, "-")

                        venue = venue_map.get(centre, ["-"])[0]
                        lab = lab_map.get(centre, ["-"])[0]

                        capacity[centre] -= 1
                        break

            # Exam type
            if cand['eng'] == 'Y' and cand['bpharm'] == 'Y':
                exam = "ENG+BPHARM"
            elif cand['eng'] == 'Y':
                exam = "ENG"
            else:
                exam = "BPHARM"

            results.append({
                "ApplNo": applno,
                "Name": cand['name'],   # ✅ now safe
                "Exam": exam,
                "Pref": pref_centre,
                "Allotted": allotted,
                "Centre Name": allotted_name,
                "Venue": venue,
                "Lab": lab
            })

        df = pd.DataFrame(results)

    # -------------------------------
    # OUTPUT
    # -------------------------------
    st.success("✅ Allotment Completed")

    st.dataframe(df, use_container_width=True)

    # -------------------------------
    # SUMMARY
    # -------------------------------
    st.subheader("📊 Summary")
    st.write(df['Allotted'].value_counts())

    # -------------------------------
    # DOWNLOAD
    # -------------------------------
    csv = df.to_csv(index=False).encode('utf-8')

    st.download_button(
        "⬇ Download Result CSV",
        csv,
        "centre_allotment.csv",
        "text/csv"
    )
