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
st.caption("Automated Dual-Rule Allocation System with Variable Column Row Capacities")

# --- 1. DYNAMIC ROOM MANAGEMENT CONTROL PANEL ---
st.header("⚙️ 1. Room Configuration Control Panel")
st.write("Specify row sizes for each column by separating them with commas (e.g., `6, 6, 5, 4` means 4 columns with those exact row sizes).")

# Initialize default rooms in session memory if not already present
if "managed_rooms" not in st.session_state:
    st.session_state.managed_rooms = [
        {"id": 1, "Room Name": "Assessment Hall", "Column_Rows_Raw": "10, 10, 10, 10, 10", "Type": "Hall"}, 
        {"id": 2, "Room Name": "6 Loyal", "Column_Rows_Raw": "6, 6, 6, 6, 6", "Type": "Classroom"},
        {"id": 3, "Room Name": "6 Peace", "Column_Rows_Raw": "6, 6, 6, 6, 6", "Type": "Classroom"},
        {"id": 4, "Room Name": "7 Grace", "Column_Rows_Raw": "6, 6, 6, 6, 6", "Type": "Classroom"}
    ]

updated_rooms = []
for idx, room in enumerate(st.session_state.managed_rooms):
    col1, col2, col3, col4 = st.columns([3, 5, 3, 1.5])
    
    with col1:
        r_name = st.text_input(f"Room Name #{idx+1}", value=room["Room Name"], key=f"name_{room['id']}")
    with col2:
        r_row_config = st.text_input(f"Row Count for each Column (comma separated)", value=room["Column_Rows_Raw"], key=f"rows_{room['id']}")
    with col3:
        type_idx = 0 if room["Type"] == "Hall" else 1
        r_type = st.selectbox(f"Room Allocation Type", ["Assessment Hall (Girls)", "Classroom (Boys)"], index=type_idx, key=f"type_{room['id']}")
        actual_type = "Hall" if "Assessment Hall" in r_type else "Classroom"
    with col4:
        st.write(" ")
        st.write(" ")
        remove_clicked = st.button("🗑️ Delete", key=f"del_{room['id']}")
        
    if not remove_clicked:
        updated_rooms.append({
            "id": room["id"],
            "Room Name": r_name.strip(),
            "Column_Rows_Raw": r_row_config.strip(),
            "Type": actual_type
        })

st.session_state.managed_rooms = updated_rooms

if st.button("➕ Add New Room"):
    next_id = max([r["id"] for r in st.session_state.managed_rooms]) + 1 if st.session_state.managed_rooms else 1
    st.session_state.managed_rooms.append({
        "id": next_id,
        "Room Name": f"New Room {next_id}",
        "Column_Rows_Raw": "6, 6, 6, 6, 6",
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
        try:
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
                
                # --- RULESET A: FEMALE SEATING (Assessment Hall) ---
                halls = [r for r in st.session_state.managed_rooms if r["Type"] == "Hall"]
                if not females.empty and halls:
                    female_classes = sorted(females['Class'].unique(), key=lambda x: int(x) if x.isdigit() else x)
                    female_queues = {c: females[females['Class'] == c].to_dict(orient='records') for c in female_classes}
                    
                    for hall in halls:
                        h_name = hall['Room Name']
                        
                        # Safe parsing for row configs per column
                        raw_parts = hall['Column_Rows_Raw'].split(",")
                        col_sizes = [int(p.strip()) for p in raw_parts if p.strip().isdigit()]
                        
                        if not col_sizes:
                            col_sizes = [10, 10, 10, 10, 10]
                        
                        max_rows = max(col_sizes)
                        num_cols = len(col_sizes)
                        
                        grid = [["[ Empty ]" for _ in range(num_cols)] for _ in range(max_rows)]
                        for c, size in enumerate(col_sizes):
                            for r in range(size, max_rows):
                                grid[r][c] = "[ No Desk ]"
                        
                        for r in range(max_rows):
                            for c in range(num_cols):
                                if grid[r][c] == "[ No Desk ]":
                                    continue
                                    
                                available_classes = [cl for cl in female_queues if len(female_queues[cl]) > 0]
                                current_row_classes = []
                                
                                for idx in range(num_cols):
                                    seat_val = grid[r][idx]
                                    if " (C-" in seat_val:
                                        extracted_class = seat_val.split(" (C-")[-1].replace(")", "")
                                        current_row_classes.append(extracted_class)
                                        
                                valid_classes = [cl for cl in available_classes if cl not in current_row_classes]
                                target_classes = valid_classes if valid_classes else available_classes
                                
                                if target_classes:
                                    chosen_class = target_classes[0]
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
                            index=[f"Seat Row {i+1}" for i in range(max_rows)], 
                            columns=[f"Table Column {j+1}" for j in range(num_cols)]
                        )

                # --- RULESET B: MALE SEATING (Classrooms) ---
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
                        
                        raw_parts = room['Column_Rows_Raw'].split(",")
                        col_sizes = [int(p.strip()) for p in raw_parts if p.strip().isdigit()]
                        
                        if not col_sizes:
                            col_sizes = [6, 6, 6, 6, 6]
                            
                        max_rows = max(col_sizes)
                        num_cols = len(col_sizes)
                        
                        grid = [["[ Empty ]" for _ in range(num_cols)] for _ in range(max_rows)]
                        for c, size in enumerate(col_sizes):
