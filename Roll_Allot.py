import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🎯 Centre Allotment (CSV / Excel Input)")

# -------------------------------
# FILE UPLOAD
# -------------------------------
lab_file = st.file_uploader("Upload Lab Details", type=["csv", "xlsx"])
pref_file = st.file_uploader("Upload Preferences", type=["csv", "xlsx"])
cand_file = st.file_uploader("Upload Candidates", type=["csv", "xlsx"])
reg_file = st.file_uploader("Upload Registrations", type=["csv", "xlsx"])


def load_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)


# -------------------------------
# MAIN PROCESS
# -------------------------------
if st.button("Run Allotment"):

    if not all([lab_file, pref_file, cand_file, reg_file]):
        st.error("Please upload all files")
        st.stop()

    with st.spinner("Processing..."):

        labs = load_file(lab_file)
        prefs = load_file(pref_file)
        candidates = load_file(cand_file)
        registrations = load_file(reg_file)

        # -------------------------------
        # 1. CAPACITY BUILD
        # -------------------------------
        capacity = {}
        centre_name = {}
        venue_map = {}
        lab_map = {}

        for _, row in labs.iterrows():
            code = row['collegecode']

            capacity[code] = capacity.get(code, 0) + row['noofsys']
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
            registrations['PaymentMode'].isin(['O', 'F'])
        ]

        merged = candidates.merge(valid_reg, left_on="ApplNo", right_on="ApplNo")

        merged = merged[
            (merged['Eng'] == 'Y') | (merged['BPharm'] == 'Y')
        ]

        merged = merged.sort_values("ApplNo")

        # -------------------------------
        # 4. ALLOTMENT
        # -------------------------------
        results = []

        for _, cand in merged.iterrows():

            applno = cand['ApplNo']

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

                        # First lab (same as your PHP)
                        venue = venue_map.get(centre, ["-"])[0]
                        lab = lab_map.get(centre, ["-"])[0]

                        capacity[centre] -= 1
                        break

            # exam type
            if cand['Eng'] == 'Y' and cand['BPharm'] == 'Y':
                exam = "ENG+BPHARM"
            elif cand['Eng'] == 'Y':
                exam = "ENG"
            else:
                exam = "BPHARM"

            results.append({
                "ApplNo": applno,
                "Name": cand['Name'],
                "Exam": exam,
                "Pref": pref_centre,
                "Allotted": allotted,
                "Centre Name": allotted_name,
                "Venue": venue,
                "Lab": lab
            })

        df = pd.DataFrame(results)

    st.success("Allotment Completed ✅")

    st.dataframe(df, use_container_width=True)

    # -------------------------------
    # DOWNLOAD
    # -------------------------------
    csv = df.to_csv(index=False).encode('utf-8')

    st.download_button(
        "Download Result CSV",
        csv,
        "centre_allotment.csv",
        "text/csv"
    )
