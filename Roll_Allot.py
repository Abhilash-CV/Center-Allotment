import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🎯 Advanced Centre Allotment System")

# -------------------------------
# FILE UPLOADS
# -------------------------------
lab_file = st.file_uploader("Lab Details", type=["csv","xlsx"])
centre_file = st.file_uploader("Centre Details", type=["csv","xlsx"])
pref_file = st.file_uploader("Preferences", type=["csv","xlsx"])
cand_file = st.file_uploader("Candidates", type=["csv","xlsx"])
reg_file = st.file_uploader("Registrations", type=["csv","xlsx"])


def load(file):
    df = pd.read_csv(file) if file.name.endswith("csv") else pd.read_excel(file)
    df.columns = df.columns.str.strip().str.lower()
    return df


if st.button("Run Allotment"):

    labs = load(lab_file)
    centres = load(centre_file)
    prefs = load(pref_file)
    candidates = load(cand_file)
    reg = load(reg_file)

    # -------------------------------
    # JOIN + FILTER
    # -------------------------------
    valid = reg[reg['paymentmode'].isin(['O','F'])]

    merged = candidates.merge(valid, on="applno", suffixes=('','_r'))
    merged = merged[(merged['eng']=='Y') | (merged['bpharm']=='Y')]
    merged = merged.sort_values("applno")

    # -------------------------------
    # CENTRE LOOKUP
    # -------------------------------
    centre_lookup = dict(zip(centres['centrecode'], centres['centrename']))

    # -------------------------------
    # CAPACITY
    # -------------------------------
    capacity = {}
    venue_map = {}
    lab_map = {}

    for _, r in labs.iterrows():
        c = r['collegecode']
        capacity[c] = capacity.get(c,0) + int(r['noofsys'])
        venue_map.setdefault(c, []).append(r['venueno'])
        lab_map.setdefault(c, []).append(r['labname'])

    # 90% rule
    for k in capacity:
        capacity[k] = int(capacity[k]*0.9)

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
                pref.append(r[col])
        pref_map[r['applno']] = pref

    # -------------------------------
    # ALLOTMENT
    # -------------------------------
    results = []

    for _, cand in merged.iterrows():

        applno = cand['applno']
        name = cand['name']

        # district priority
        district = cand.get('cdistrict', None)

        if applno not in pref_map:
            continue

        pref_list = pref_map[applno]

        # sort centres by same district first
        pref_list = sorted(pref_list, key=lambda x: 0 if str(x)==str(district) else 1)

        for centre in pref_list:

            if centre not in slot:
                continue

            # ---------------------
            # DUAL EXAM
            # ---------------------
            if cand['eng']=='Y' and cand['bpharm']=='Y':

                # pick least loaded day
                days_sorted = sorted(BPHARM_DAYS, key=lambda d: usage[centre][(d,"MORNING")])

                for d in days_sorted:

                    k1 = (d,"MORNING","BPHARM")
                    k2 = (d,"AFTERNOON","ENG")

                    if slot[centre][k1]>0 and slot[centre][k2]>0:

                        slot[centre][k1]-=1
                        slot[centre][k2]-=1

                        usage[centre][(d,"MORNING")]+=1
                        usage[centre][(d,"AFTERNOON")]+=1

                        v = venue_map[centre][0]
                        l = lab_map[centre][0]

                        results.append([applno,name,"BPHARM",d,"MORNING",centre,v,l])
                        results.append([applno,name,"ENG",d,"AFTERNOON",centre,v,l])
                        break
                break

            # ---------------------
            # ENG ONLY
            # ---------------------
            elif cand['eng']=='Y':

                days_sorted = sorted(ENG_DAYS, key=lambda d: usage[centre][(d,"AFTERNOON")])

                for d in days_sorted:
                    k = (d,"AFTERNOON","ENG")

                    if slot[centre][k]>0:
                        slot[centre][k]-=1
                        usage[centre][(d,"AFTERNOON")]+=1

                        v = venue_map[centre][0]
                        l = lab_map[centre][0]

                        results.append([applno,name,"ENG",d,"AFTERNOON",centre,v,l])
                        break
                break

            # ---------------------
            # BPHARM ONLY
            # ---------------------
            else:

                days_sorted = sorted(BPHARM_DAYS, key=lambda d: usage[centre][(d,"MORNING")])

                for d in days_sorted:
                    k = (d,"MORNING","BPHARM")

                    if slot[centre][k]>0:
                        slot[centre][k]-=1
                        usage[centre][(d,"MORNING")]+=1

                        v = venue_map[centre][0]
                        l = lab_map[centre][0]

                        results.append([applno,name,"BPHARM",d,"MORNING",centre,v,l])
                        break
                break

    df = pd.DataFrame(results, columns=[
        "ApplNo","Name","Exam","Day","Session","Centre","Venue","Lab"
    ])

    st.success("✅ Completed")

    st.dataframe(df, use_container_width=True)

    # -------------------------------
    # DASHBOARD
    # -------------------------------
    st.subheader("📊 Centre Utilization")
    st.write(df['Centre'].value_counts())

    st.subheader("📅 Day-wise Load")
    st.write(df['Day'].value_counts().sort_index())

    st.subheader("🕒 Session Distribution")
    st.write(df['Session'].value_counts())

    # download
    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode(),
        "allotment.csv"
    )
