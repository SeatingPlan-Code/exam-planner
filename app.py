import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Sandeepni School Seating Planner", layout="wide")

# CSS styling to eliminate massive visual blocks and prevent layout clipping
st.markdown("""
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 1.5rem;}
    h1, h2, h3 {margin-bottom: 0.3rem; padding-top: 0.5rem;}
    div.stDataFrame {border: 1px solid #e6e9ef; border-radius: 4px;}
    .stNumberInput, .stTextInput, .stSelectbox {margin-bottom: 0.2rem;}
    </style>
""", unsafe_allow_html=True)

st.title("🏫 Sandeepni School Exam Seating Manager")
st.caption("Automated Dual-Rule Allocation System with Dynamic Room Configuration Control")

# --- 1. DYNAMIC ROOM MANAGEMENT CONTROL PANEL ---
st.header("⚙️ 1. Room Configuration Control Panel")
st.write("Add, remove, or modify your exam rooms below before uploading your student list.")

# Initialize default rooms in session memory if not already present
if "managed_rooms" not in st.session_state:
    st.session_state.managed_rooms = [
        {"id": 1, "Room Name": "Assessment Hall", "Rows": 10, "Columns": 5, "Type": "Hall"}, 
        {"id": 2, "Room Name": "6 Loyal", "Rows": 6, "Columns": 5, "Type": "Classroom"},
        {"id": 3, "Room Name": "6 Peace", "Rows": 6, "Columns": 5, "Type": "Classroom"},
        {"id": 4, "Room Name": "7 Grace", "Rows": 6, "Columns": 5, "Type": "Classroom"}
    ]

updated_rooms = []
for idx, room in enumerate(st.session_state.managed_rooms):
    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 3, 1.5])
    
    with col1:
        r_name = st.text_input(f"Room Name #{idx+1}", value=room["Room Name"], key=f"name_{room['id']}")
    with col2:
        r_rows = st.number_input(f"Rows", min_value=1, max_value=50, value=room["Rows"], key=f"rows_{room['id']}")
    with col3:
        r_cols = st.number_input(f"Columns", min_value=1, max_value=50, value=room["Columns"], key=f"cols_{room['id']}")
    with col4:
        type_idx = 0 if room["Type"] == "Hall" else 1
        r_type = st.selectbox(f"Room Allocation Type", ["Assessment Hall (Girls)", "Classroom (Boys)"], index=type_idx, key=f"type_{room['id']}")
        actual_type = "Hall" if "Assessment Hall" in r_type else "Classroom"
    with col5:
        st.write(" ")
        st.write(" ")
        remove_clicked = st.button("🗑️ Delete", key=f"del_{room['id']}")
        
    if not remove_clicked:
        updated_rooms.append({
            "id": room["id"],
            "Room Name": r_name.strip(),
            "Rows": int(r_rows),
            "Columns": int(r_cols),
            "Type": actual_type
        })

st.session_state.managed_rooms = updated_rooms

if st.button("➕ Add New Room"):
    next_id = max([r["id"] for r in st.session_state.managed_rooms]) + 1 if st.session_state.managed_rooms else 1
    st.session_state.managed_rooms.append({
        "id": next_id,
        "Room Name": f"New Room {next_id}",
        "Rows": 6,
        "Columns": 5,
        "Type": "Classroom"
    })
    st.rerun()

st.markdown("---")

# --- 2. DATA INPUT SECTION ---
st.header("📂 2. Upload Master Student List")
stud_file = st.file_uploader("Upload your Master Excel Sheet (.xlsx)", type=["xlsx"])

if stud_file:
    if not st.session_state.managed_rooms:
        st.error("❌ Cannot process allocation: Please add at least one room above.")
    else:
        df_stud = pd.read_excel(stud_file)
        df_stud.columns = df_stud.columns.str.strip()
        
        required_cols = ["House Number", "Name", "Class", "Section", "Gender"]
        missing_cols = [col for col in required_cols if col not in df_stud.columns]
        
        if missing_cols:
            st.error(f"❌ Error: The uploaded file is missing these required columns: {missing_cols}")
        else:
            # Standardize inputs
            df_stud['Gender'] = df_stud['Gender'].astype(str).str.strip().str.upper()
            df_stud['Class'] = df_stud['Class'].astype(str).str.strip()
            df_stud['Section'] = df_stud['Section'].astype(str).str.strip()
            df_stud['House Number'] = df_stud['House Number'].astype(str).str.strip()
            
            has_sr_no = "Sr. No" in df_stud.columns
            if has_sr_no:
                df_stud['Sr. No'] = df_stud['Sr. No'].astype(str).str.strip()
            
            females = df_stud[df_stud['Gender'] == 'FEMALE'].copy()
            males = df_stud[df_stud['Gender'] == 'MALE'].copy()
            
            master_registry = []
            room_layouts = {}
            
            # --- RULESET A: FEMALE SEATING (Assessment Hall - Multi-Class Tables) ---
            halls = [r for r in st.session_state.managed_rooms if r["Type"] == "Hall"]
            if not females.empty and halls:
                female_classes = sorted(females['Class'].unique(), key=lambda x: int(x) if x.isdigit() else x)
                female_queues = {c: females[females['Class'] == c].to_dict(orient='records') for c in female_classes}
                
                for hall in halls:
                    h_name = hall['Room Name']
                    h_rows = hall['Rows']
                    h_cols = hall['Columns'] 
                    
                    grid = [["[ Empty ]" for _ in range(h_cols)] for _ in range(h_rows)]
                    
                    for r in range(h_rows):
                        for c in range(h_cols):
                            available_classes = [cl for cl in female_queues if len(female_queues[cl]) > 0]
                            current_row_classes = []
                            
                            for idx in range(h_cols):
                                seat_val = grid[r][idx]
                                if " (C-" in seat_val:
                                    extracted_class = seat_val.split(" (C-")[-1].replace(")", "")
                                    current_row_classes.append(extracted_class)
                                    
                            valid_classes = [cl for cl in available_classes if cl not in current_row_classes]
                            target_classes = valid_classes if valid_classes else available_classes
                            
                            if target_classes:
                                chosen_class = target_classes
                                student = female_queues[chosen_class].pop(0)
                                grid[r][c] = f"{student['Name']} (C-{chosen_class})"
                                
                                row_data = {
                                    "House Number": student['House Number'],
                                    "Name": student['Name'],
                                    "Class": student['Class'],
                                    "Section": student['Section'],
                                    "Gender": "Female",
                                    "Assigned Classroom/Hall": h_name,
                                    "Column Number": c + 1,
                                    "Seat Number": r + 1
                                }
                                if has_sr_no:
                                    row_data = {"Sr. No": student['Sr. No'], **row_data}
                                master_registry.append(row_data)
                    
                    room_layouts[h_name] = pd.DataFrame(
                        grid, 
                        index=[f"Seat Row {i+1}" for i in range(h_rows)], 
                        columns=[f"Table Column {j+1}" for j in range(h_cols)]
                    )

            # --- RULESET B: MALE SEATING (Classrooms - Sequential Class Rollover) ---
            classrooms = [r for r in st.session_state.managed_rooms if r["Type"] == "Classroom"]
            if not males.empty and classrooms:
                male_classes = sorted(males['Class'].unique(), key=lambda x: int(x) if x.isdigit() else x)
                male_stream = []
                
                for mc in male_classes:
                    male_stream.extend(males[males['Class'] == mc].to_dict(orient='records'))
                    
                m_idx = 0
                total_males = len(male_stream)
                
                for room in classrooms:
                    r_name = room['Room Name']
                    r_rows = room['Rows']
                    r_cols = room['Columns']
                    
                    grid = [["[ Empty ]" for _ in range(r_cols)] for _ in range(r_rows)]
                    
                    for r in range(r_rows):
                        for c in range(r_cols):
                            if m_idx < total_males:
                                student = male_stream[m_idx]
                                grid[r][c] = f"{student['Name']} (C-{student['Class']})"
                                
                                row_data = {
                                    "House Number": student['House Number'],
                                    "Name": student['Name'],
                                    "Class": student['Class'],
                                    "Section": student['Section'],
                                    "Gender": "Male",
                                    "Assigned Classroom/Hall": r_name,
                                    "Column Number": c + 1,
                                    "Seat Number": r + 1
                                }
                                if has_sr_no:
                                    row_data = {"Sr. No": student['Sr. No'], **row_data}
                                    
                                master_registry.append(row_data)
                                m_idx += 1
                                
                    room_layouts[r_name] = pd.DataFrame(
                        grid, 
                        index=[f"Row {i+1}" for i in range(r_rows)], 
                        columns=[f"Column {j+1}" for j in range(r_cols)])
