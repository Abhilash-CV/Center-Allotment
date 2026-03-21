import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🎯 Centre Allotment System (CSV / Excel)")

# -------------------------------
# FILE UPLOAD
# -------------------------------
lab_file = st.file_uploader("Upload Lab Details", type=["csv", "xlsx"])
pref_file = st.file_uploader("Upload Preferences", type=["csv", "xlsx"])
cand_file = st.file_uploader("Upload Candidates", type=["csv", "xlsx"])
reg_file = st.file_uploader("Upload Registrations", type=["csv", "xlsx"])


# -------------------------------
# FILE LOADER
# -------------------------------
def load_file(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    # Normalize column names (CRITICAL FIX)
    df.columns = df.columns.str.strip().str.lower()
    return df


# -------------------------------
# VALIDATION FUNCTION
# -------------------------------
def validate_columns(df, required_cols, file_name):
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"❌ Missing columns in {file_name}: {missing}")
        st.write("Available columns:", df.columns.tolist())
        st.stop()


# -------------------------------
# MAIN PROCESS
# -------------------------------
if st.button("Run Allotment"):

    if not all([lab_file, pref_file, cand_file, reg_file]):
        st.error("⚠️ Please upload all required files")
        st.stop()

    with st.spinner("Processing..."):

        # Load files
        labs = load_file(lab_file)
        prefs = load_file(pref_file)
        candidates = load_file(cand_file)
        registrations = load_file(reg_file)

        # Debug: show columns
        with st.expander("🔍 Debug: View Columns"):
            st.write("Lab:", labs.columns.tolist())
            st.write("Prefs:", prefs.columns.tolist())
            st.write("Candidates:", candidates.columns.tolist())
            st.write("Registrations:", registrations.columns.tolist())

        # -------------------------------
        # VALIDATE STRUCTURE
        # -------------------------------
        validate_columns(labs,
            ['collegecode', 'centrename', 'venueno', 'labname', 'noofsys'],
            "Lab Details"
        )

        validate_columns(prefs, ['applno'], "Preferences")
        validate_columns(candidates, ['applno', 'name', 'eng', 'bpharm'], "Candidates")
        validate_columns(registrations, ['applno', 'paymentmode'], "Registrations")

        # -------------------------------
        # 1. CAPACITY BUILD
        # -------------------------------
        capacity = {}
        centre_name = {}
        venue_map = {}
        lab_map = {}

        for _, row in labs.iterrows():
            code = row['collegecode']

            capacity[code] = capacity.get(code, 0) + int(row['noofsys'])
            centre_name[code] = row['centrename']

            venue_map.setdefault(code, []).append(row['venueno'])
            lab_map.setdefault(code, []).append(row['labname'])

        # Apply 10% buffer
        for k in capacity:
            capacity[k] = int(capacity[k] * 0.90)

        # -------------------------------
        # 2. PREFERENCE MAP
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
        # 3. FILTER VALID CANDIDATES
        # -------------------------------
        valid_reg = registrations[
            registrations['paymentmode'].isin(['O', 'F'])
        ]

        merged = candidates.merge(valid_reg, on="applno")

        merged = merged[
            (merged['eng'] == 'Y') | (merged['bpharm'] == 'Y')
        ]

        merged = merged.sort_values("applno")

        # -------------------------------
        # 4. ALLOTMENT
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

                        # Default: first lab (same as PHP)
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
                "Name": cand['name'],
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
