import streamlit as st
import pandas as pd
from datetime import datetime
import os
import json
import shutil
import random

# Constants
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
EXERCISES_FILE = os.path.join(DATA_DIR, "exercises.json")
WORKOUTS_FILE = os.path.join(DATA_DIR, "workouts.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archived_users")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

# Create data directory if it doesn't exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Update constants to include user-specific paths
def get_user_data_path(username):
    """Get path to user-specific data directory"""
    return os.path.join(DATA_DIR, username)

def get_user_files(username):
    """Get paths to user-specific data files"""
    user_dir = get_user_data_path(username)
    return {
        'exercises': os.path.join(user_dir, "exercises.json"),
        'workouts': os.path.join(user_dir, "workouts.json")
    }

# Update init_data_storage to handle user-specific directories
def init_data_storage():
    """Initialize data storage files in the 'data' directory"""
    for directory in [DATA_DIR, ARCHIVE_DIR, BACKUP_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    # Initialize only users file if it doesn't exist
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({"users": []}, f)

def init_user_storage(username):
    """Initialize storage for a specific user"""
    user_dir = get_user_data_path(username)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    
    user_files = get_user_files(username)
    default_data = {
        user_files['exercises']: {"exercises": []},
        user_files['workouts']: {"workouts": []}
    }
    
    for file_path, default_content in default_data.items():
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump(default_content, f)

def create_backup():
    """Create a backup of all user data"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}")
    
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)
    
    # Backup users file
    shutil.copy2(USERS_FILE, os.path.join(backup_path, "users.json"))
    
    # Backup each user's data
    users = load_users()
    for user in users:
        username = user['name']
        user_dir = get_user_data_path(username)
        if os.path.exists(user_dir):
            user_backup_dir = os.path.join(backup_path, username)
            shutil.copytree(user_dir, user_backup_dir)
    
    # Keep only last 5 backups
    backups = sorted([d for d in os.listdir(BACKUP_DIR) if d.startswith('backup_')])
    if len(backups) > 5:
        for old_backup in backups[:-5]:
            shutil.rmtree(os.path.join(BACKUP_DIR, old_backup))

def save_user(name):
    users = load_users()
    # Check if user already exists
    if any(user['name'] == name for user in users):
        return False, "User already exists"
    
    # Generate a protection code for the user
    protection_code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    
    users.append({
        "id": len(users) + 1,
        "name": name,
        "created_at": datetime.now().isoformat(),
        "protection_code": protection_code  # Add protection code
    })
    with open(USERS_FILE, 'w') as f:
        json.dump({"users": users}, f)
    
    # Initialize storage for new user
    init_user_storage(name)
    return True, f"Added user: {name}\nYour protection code is: {protection_code}\nPlease save this code - you'll need it to delete your data."

def delete_user(name):
    """Archive a user's data and remove them from active users"""
    # Get user's protection code
    users = load_users()
    user = next((u for u in users if u['name'] == name), None)
    if not user:
        return False, "User not found"
    
    # Ask for protection code
    protection_code = st.text_input("Enter protection code to delete user:", type="password")
    if not protection_code:
        return False, "Please enter the protection code"
    
    if protection_code != user.get('protection_code'):
        return False, "Incorrect protection code"
    
    # Create backup before deletion
    create_backup()
    
    # Proceed with deletion
    users = [u for u in users if u['name'] != name]
    with open(USERS_FILE, 'w') as f:
        json.dump({"users": users}, f)
    
    user_dir = get_user_data_path(name)
    if os.path.exists(user_dir):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_user_dir = os.path.join(ARCHIVE_DIR, f"{name}_{timestamp}")
        shutil.move(user_dir, archive_user_dir)
    
    return True, f"Deleted user: {name}"

# Update data loading functions to use user-specific files
def load_exercises(username):
    user_files = get_user_files(username)
    with open(user_files['exercises'], 'r') as f:
        data = json.load(f)
        return data["exercises"]

def load_workouts(username):
    user_files = get_user_files(username)
    with open(user_files['workouts'], 'r') as f:
        data = json.load(f)
        return data["workouts"]

# Update save functions to use user-specific files
def save_exercise(name, muscle_group, username):
    exercises = load_exercises(username)
    normalized_name = normalize_exercise_name(name)
    
    # Check if exercise already exists
    for i, ex in enumerate(exercises):
        if normalize_exercise_name(ex['name']) == normalized_name:
            exercises[i] = {
                "name": normalized_name,
                "muscle_group": muscle_group,
                "created_at": ex['created_at']
            }
            break
    else:
        exercises.append({
            "name": normalized_name,
            "muscle_group": muscle_group,
            "created_at": datetime.now().isoformat()
        })
    
    user_files = get_user_files(username)
    with open(user_files['exercises'], 'w') as f:
        json.dump({"exercises": exercises}, f)

def save_workout(exercise, weight, reps, username):
    workouts = load_workouts(username)
    workouts.append({
        "date": datetime.now().strftime('%Y-%m-%d'),
        "exercise": exercise,
        "weight": weight,
        "reps": reps
    })
    user_files = get_user_files(username)
    with open(user_files['workouts'], 'w') as f:
        json.dump({"workouts": workouts}, f)

def load_users():
    with open(USERS_FILE, 'r') as f:
        data = json.load(f)
        return data["users"]

def normalize_exercise_name(name):
    """Normalize exercise name: lowercase and strip extra spaces"""
    return " ".join(name.lower().split())

def import_from_csv(file, username):
    """Import workout data from CSV file for specific user"""
    try:
        df = pd.read_csv(file)
        # close the file
        file.close()
        required_columns = ['date', 'exercise', 'weight', 'reps']
        
        if not all(col in df.columns for col in required_columns):
            return False, "CSV must contain columns: date, exercise, weight, reps"
        
        df['exercise'] = df['exercise'].apply(normalize_exercise_name)
        
        # Add new exercises to user's exercise database
        existing_exercises = load_exercises(username)
        existing_names = {normalize_exercise_name(ex['name']) for ex in existing_exercises}
        
        new_exercises = []
        for exercise_name in df['exercise'].unique():
            exercise_name = exercise_name.strip()
            if exercise_name not in existing_names:
                new_exercises.append({
                    "name": exercise_name,
                    "muscle_group": "Other",
                    "created_at": datetime.now().isoformat()
                })
        
        if new_exercises:
            existing_exercises.extend(new_exercises)
            user_files = get_user_files(username)
            with open(user_files['exercises'], 'w') as f:
                json.dump({"exercises": existing_exercises}, f)
        
        # Import workout data
        workouts = load_workouts(username)
        new_workouts = df.to_dict('records')
        
        for workout in new_workouts:
            date = pd.to_datetime(workout['date']).strftime('%Y-%m-%d')
            workouts.append({
                "date": date,
                "exercise": workout['exercise'],
                "weight": float(workout.get('weight', 0)),
                "reps": int(workout['reps'])
            })
        
        user_files = get_user_files(username)
        with open(user_files['workouts'], 'w') as f:
            json.dump({"workouts": workouts}, f)
        
        message = f"Imported {len(new_workouts)} workouts"
        if new_exercises:
            message += f" and added {len(new_exercises)} new exercises. Please categorize them in the Exercises tab."
        
        return True, message
    except Exception as e:
        return False, f"Error importing data: {str(e)}"

def delete_workout(workout_index):
    """Delete a workout entry by its index"""
    workouts = load_workouts()
    if 0 <= workout_index < len(workouts):
        deleted = workouts.pop(workout_index)
        with open(WORKOUTS_FILE, 'w') as f:
            json.dump({"workouts": workouts}, f)
        return True, f"Deleted: {deleted['exercise']} - {deleted['reps']} reps"
    return False, "Invalid workout index"

def get_last_workout(exercise, username):
    """Get the most recent workout for given exercise and user"""
    workouts = load_workouts(username)
    if not workouts:
        return None
    
    df = pd.DataFrame(workouts)
    # Handle date parsing with mixed formats
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    
    # Filter for exercise
    exercise_df = df[df['exercise'] == exercise].sort_values('date', ascending=False)
    
    if not exercise_df.empty:
        return exercise_df.iloc[0]
    return None

def log_workout():
    st.subheader("Log Workout")
    
    exercises = load_exercises(st.session_state.current_user)
    exercise_names = sorted([ex["name"] for ex in exercises], key=str.lower)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        exercise = st.selectbox(
            "Exercise",
            options=exercise_names if exercise_names else ["Add exercises first"],
            placeholder="Select exercise",
            key="workout_exercise_select"
        )
        
        if exercise and exercise != "Add exercises first":
            last_workout = get_last_workout(exercise, st.session_state.current_user)
        else:
            last_workout = None
    
    with col2:
        weight = st.number_input(
            "Weight (kg)",
            min_value=0.0,
            max_value=500.0,
            step=1.0,
            format="%g",
            value=float(last_workout['weight']) if last_workout is not None else 0.0,
            key="workout_weight_input"
        )
    
    with col3:
        reps = st.number_input(
            "Reps",
            min_value=0,
            max_value=100,
            step=1,
            value=int(last_workout['reps']) if last_workout is not None else 0,
            key="workout_reps_input"
        )
    
    if st.button("Log Set", type="primary", key="log_set_button"):
        if exercise and exercise != "Add exercises first":
            if reps > 0:
                save_workout(exercise, weight, reps, st.session_state.current_user)
                st.success("Set logged successfully!")
            else:
                st.error("Please enter number of reps")
        else:
            st.error("Please select an exercise (or add exercises first)")
    
    # Show recent workouts
    show_recent_workouts()
    
    # Show progress chart only for selected exercise
    if exercise and exercise != "Add exercises first":
        st.write("### Exercise Progress")
        workouts = load_workouts(st.session_state.current_user)
        if workouts:
            df = pd.DataFrame(workouts)
            df['date'] = pd.to_datetime(df['date'], format='mixed')
            
            # Filter data for selected exercise
            exercise_data = df[df['exercise'] == exercise].sort_values('date')
            
            if not exercise_data.empty:
                fig = create_progress_chart(exercise_data, exercise)
                st.plotly_chart(fig)
            else:
                st.info(f"No workout data yet for {exercise}")

def delete_exercise(name, username):
    """Delete an exercise from the database"""
    exercises = load_exercises(username)
    exercises = [ex for ex in exercises if ex['name'] != name]
    user_files = get_user_files(username)
    with open(user_files['exercises'], 'w') as f:
        json.dump({"exercises": exercises}, f)

def manage_exercises():
    st.subheader("Exercise Management")
    
    # Sort muscle groups alphabetically
    MUSCLE_GROUPS = sorted(["Arms", "Back", "Chest", "Core", "Full Body", "Legs", "Shoulders", "Other"])
    
    # Add new exercise
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    
    with col1:
        # Get existing exercise names
        exercises = load_exercises(st.session_state.current_user)
        # Sort exercise names case-insensitively
        existing_names = sorted([ex["name"] for ex in exercises], key=str.lower)
        
        # Add "Add New" option at the top
        exercise_options = ["Add New"] + existing_names
        selected_exercise = st.selectbox(
            "Exercise Name",
            options=exercise_options,
            key="exercise_select"
        )
        
        # Show text input if "Add New" is selected
        if selected_exercise == "Add New":
            new_exercise = st.text_input("New Exercise Name", key="new_exercise_input")
        else:
            new_exercise = selected_exercise
            
    with col2:
        muscle_group = st.selectbox(
            "Muscle Group", 
            MUSCLE_GROUPS,
            key="muscle_group_select"
        )
    
    with col3:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("Add/Update Exercise", type="primary", key="add_update_button"):
            if new_exercise and new_exercise != "Add New":
                save_exercise(new_exercise, muscle_group, st.session_state.current_user)
                st.success(f"Added/Updated {new_exercise}")
            else:
                st.error("Please enter exercise name")
    
    with col4:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if selected_exercise != "Add New":
            if st.button("🗑️ Delete", type="secondary", help="Delete selected exercise", key="delete_button"):
                if selected_exercise:
                    delete_exercise(selected_exercise, st.session_state.current_user)
                    st.success(f"Deleted {selected_exercise}")
    
    # Show existing exercises with editable muscle groups
    if exercises:
        st.write("### Exercise Library")
        
        # Convert to DataFrame for display
        df = pd.DataFrame(exercises)
        df = df.rename(columns={
            'name': 'Exercise',
            'muscle_group': 'Muscle Group',
            'created_at': 'Added On'
        })
        df['Added On'] = pd.to_datetime(df['Added On']).dt.strftime('%Y-%m-%d')
        
        # Create editable dataframe
        edited_df = st.data_editor(
            df[['Exercise', 'Muscle Group', 'Added On']].sort_values('Exercise'),
            column_config={
                "Exercise": st.column_config.Column(
                    width="medium",
                    disabled=True
                ),
                "Muscle Group": st.column_config.SelectboxColumn(
                    width="medium",
                    options=MUSCLE_GROUPS,
                    required=True
                ),
                "Added On": st.column_config.Column(
                    width="small",
                    disabled=True
                )
            },
            hide_index=True,
            key="exercise_editor"
        )
        
        # Check for changes and update muscle groups
        if edited_df is not None and not df['Muscle Group'].equals(edited_df['Muscle Group']):
            # Update exercises in storage
            updated_exercises = []
            for _, row in edited_df.iterrows():
                exercise_name = row['Exercise']
                new_muscle_group = row['Muscle Group']
                # Find original exercise and update muscle group
                for ex in exercises:
                    if ex['name'] == exercise_name:
                        updated_exercises.append({
                            'name': ex['name'],
                            'muscle_group': new_muscle_group,
                            'created_at': ex['created_at']
                        })
                        break
            
            # Save updated exercises to user-specific file
            user_files = get_user_files(st.session_state.current_user)
            with open(user_files['exercises'], 'w') as f:
                json.dump({"exercises": updated_exercises}, f)
            
            st.success("Updated muscle groups")

def show_recent_workouts():
    workouts = load_workouts(st.session_state.current_user)
    if workouts:
        df = pd.DataFrame(workouts)
        
        if df.empty:
            st.info(f"No workouts logged yet for {st.session_state.current_user}")
            return
            
        # Handle date parsing with mixed formats
        df['date'] = pd.to_datetime(df['date'], format='mixed')
        
        # Sort dates in descending order and get unique dates
        unique_dates = df['date'].dt.strftime('%d %b').unique()
        unique_dates = sorted(unique_dates, reverse=True)
        
        # Get unique exercises for this user
        exercises = sorted(df['exercise'].unique())
        
        # Create pivot table data
        pivot_data = []
        for exercise in exercises:
            row = {'Exercise': exercise}
            exercise_data = df[df['exercise'] == exercise]
            
            for date in unique_dates:
                date_data = exercise_data[exercise_data['date'].dt.strftime('%d %b') == date]
                if not date_data.empty:
                    # Combine all sets for this date
                    sets = []
                    for _, set_data in date_data.iterrows():
                        sets.append(f"{set_data['weight']}kg × {set_data['reps']}")
                    row[date] = ", ".join(sets)
                else:
                    row[date] = ""
            
            pivot_data.append(row)
        
        # Create display dataframe
        display_df = pd.DataFrame(pivot_data)
        
        st.write(f"### Recent Workouts for {st.session_state.current_user}")
        
        # Show the pivot table
        st.data_editor(
            display_df,
            column_config={
                "Exercise": st.column_config.Column(
                    width="medium",
                ),
                **{date: st.column_config.Column(
                    width="large",
                ) for date in unique_dates}
            },
            hide_index=True,
            disabled=True
        )

def show_analytics():
    st.subheader("Analytics")
    workouts = load_workouts(st.session_state.current_user)
    
    if not workouts:
        st.info("No workout data available yet")
        return
    
    df = pd.DataFrame(workouts)
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    
    # Weekly comparison
    st.write("### Weekly Comparison")
    today = pd.Timestamp.now()
    last_week = df[df['date'] > (today - pd.Timedelta(days=14))]
    if not last_week.empty:
        this_week = last_week[last_week['date'] > (today - pd.Timedelta(days=7))]
        prev_week = last_week[last_week['date'] <= (today - pd.Timedelta(days=7))]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("This Week Workouts", len(this_week))
        with col2:
            st.metric("Last Week Workouts", len(prev_week))
    
    # Combined progress chart for all exercises
    st.write("### Combined Exercise Progress")
    
    import plotly.graph_objects as go
    
    fig = go.Figure()
    
    # Get unique exercises and sort them case-insensitively
    exercises = sorted(df['exercise'].unique(), key=str.lower)
    
    # Add a line for each exercise
    for exercise in exercises:
        exercise_data = df[df['exercise'] == exercise].sort_values('date')
        daily_max = exercise_data.groupby(exercise_data['date'].dt.date)['weight'].max().reset_index()
        
        fig.add_trace(go.Scatter(
            x=daily_max['date'],
            y=daily_max['weight'],
            mode='lines+markers',
            name=exercise,
            line=dict(width=2),
            marker=dict(size=6)
        ))
    
    # Update layout to ensure x-axis shows full date range
    fig.update_layout(
        title="All Exercises Progress",
        xaxis_title="Date",
        yaxis_title="Weight (kg)",
        height=600,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        xaxis=dict(
            rangeslider=dict(visible=True),  # Add range slider
            type="date"  # Ensure proper date handling
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_progress_chart(exercise_data, exercise_name):
    """Create a progress chart for an exercise"""
    import plotly.graph_objects as go
    
    # Get max weight per day - no date filtering
    daily_max = exercise_data.groupby(exercise_data['date'].dt.date)['weight'].max().reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_max['date'],
        y=daily_max['weight'],
        mode='lines+markers',
        name='Max Weight',
        line=dict(width=2),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title=f"{exercise_name} Progress",
        xaxis_title="Date",
        yaxis_title="Weight (kg)",
        height=400,
        showlegend=False,
        xaxis=dict(
            rangeslider=dict(visible=True),  # Add range slider
            type="date"  # Ensure proper date handling
        )
    )
    
    return fig

def import_exercises_from_csv(file, username):
    """Import exercises from CSV to the exercise database"""
    try:
        df = pd.read_csv(file)
        
        # Get existing exercises
        existing = load_exercises(username)
        existing_names = {ex['name'].lower() for ex in existing}
        
        # Process new exercises
        new_exercises = []
        for _, row in df.iterrows():
            exercise_name = row['exercise'].strip()
            if exercise_name.lower() not in existing_names:
                new_exercises.append({
                    "name": exercise_name,
                    "muscle_group": "Other",  # Default to "Other" for imported exercises
                    "created_at": datetime.now().isoformat()
                })
        
        if new_exercises:
            existing.extend(new_exercises)
            user_files = get_user_files(username)
            with open(user_files['exercises'], 'w') as f:
                json.dump({"exercises": existing}, f)
            
            return True, f"Added {len(new_exercises)} new exercises. Please categorize them in the Exercises tab."
        return True, "No new exercises to add"
        
    except Exception as e:
        return False, f"Error importing exercises: {str(e)}"

def get_unique_export_filename(base_filename):
    """Generate unique filename by adding counter if file exists"""
    filename = base_filename
    counter = 1
    
    while os.path.exists(os.path.join(APP_DIR, filename)):
        # Split filename into name and extension
        name, ext = os.path.splitext(base_filename)
        filename = f"{name}_{counter}{ext}"
        counter += 1
    
    return filename

# Add new function to get archived users
def get_archived_users():
    """Get list of archived users from archive directory"""
    if not os.path.exists(ARCHIVE_DIR):
        return []
    
    archived_users = []
    for user_dir in os.listdir(ARCHIVE_DIR):
        # Split username from timestamp
        username = user_dir.rsplit('_', 1)[0]
        archived_users.append(username)
    
    # Return unique usernames sorted alphabetically
    return sorted(set(archived_users))

def restore_user(username):
    """Restore a user from archive"""
    # Find most recent archive for this user
    user_archives = [d for d in os.listdir(ARCHIVE_DIR) if d.startswith(username + '_')]
    if not user_archives:
        return False, f"No archive found for {username}"
    
    # Sort by timestamp to get most recent
    latest_archive = sorted(user_archives)[-1]
    archive_path = os.path.join(ARCHIVE_DIR, latest_archive)
    
    # Check if user already exists
    users = load_users()
    if any(user['name'] == username for user in users):
        return False, f"User {username} already exists"
    
    try:
        # Add user back to users list
        users.append({
            "id": len(users) + 1,
            "name": username,
            "created_at": datetime.now().isoformat()
        })
        with open(USERS_FILE, 'w') as f:
            json.dump({"users": users}, f)
        
        # Initialize storage for the restored user
        init_user_storage(username)
        
        # Remove existing user directory if it exists (cleanup)
        user_dir = get_user_data_path(username)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
        
        # Copy data from archive
        shutil.copytree(archive_path, user_dir)
        
        # Remove the archive
        shutil.rmtree(archive_path)
        
        return True, f"Restored user: {username}"
    except Exception as e:
        return False, f"Error restoring user: {str(e)}"

def create_backup_file():
    """Create a backup file for download"""
    backup_data = {
        'timestamp': datetime.now().isoformat(),
        'users': [],
        'user_data': {}
    }
    
    # Get users data
    with open(USERS_FILE, 'r') as f:
        users_data = json.load(f)
        backup_data['users'] = users_data['users']
    
    # Get each user's data
    for user in backup_data['users']:
        username = user['name']
        user_files = get_user_files(username)
        user_data = {}
        
        try:
            # Get exercises
            with open(user_files['exercises'], 'r') as f:
                user_data['exercises'] = json.load(f)
            
            # Get workouts
            with open(user_files['workouts'], 'r') as f:
                user_data['workouts'] = json.load(f)
            
            backup_data['user_data'][username] = user_data
        except:
            continue
    
    return json.dumps(backup_data, indent=2)

def restore_from_backup_file(backup_content):
    """Restore data from a backup file"""
    try:
        backup_data = json.loads(backup_content)
        
        # Restore users
        with open(USERS_FILE, 'w') as f:
            json.dump({"users": backup_data['users']}, f)
        
        # Restore each user's data
        for username, user_data in backup_data['user_data'].items():
            # Create user directory
            init_user_storage(username)
            user_files = get_user_files(username)
            
            # Save exercises
            with open(user_files['exercises'], 'w') as f:
                json.dump(user_data['exercises'], f)
            
            # Save workouts
            with open(user_files['workouts'], 'w') as f:
                json.dump(user_data['workouts'], f)
        
        return True, "Backup restored successfully"
    except Exception as e:
        return False, f"Error restoring backup: {str(e)}"

def check_password():
    """Returns `True` if the user had the correct password."""
    if not st.session_state.get("password_correct", False):
        # First run or incorrect password
        password = st.sidebar.text_input("Enter password", type="password")
        if password:
            # Get password from secrets or use default for development
            correct_password = st.secrets.get("password", "admin")  # Default password for development
            if password == correct_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.sidebar.error("Incorrect password")
        return False
    return True

def main():
    if not check_password():
        st.title("Fitness Tracker")
        st.write("Please enter the password to access this app.")        
        st.stop()
    
    st.title("Fitness Tracker")
    
    # Initialize data storage
    init_data_storage()
    
    # User selection and data management in sidebar
    with st.sidebar:
        st.subheader("User Management")
        
        # Add tabs for active users, archived users, and backup
        user_tab1, user_tab2, user_tab3 = st.tabs(["Active Users", "Archived Users", "Backup"])
        
        with user_tab1:
            # Add new user section
            new_user = st.text_input("Add New User")
            col1, col2 = st.columns([4, 1])
            with col2:
                add_clicked = st.button("Add", type="primary")
            
            # Handle add user action
            if add_clicked:
                if new_user:
                    success, message = save_user(new_user)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Please enter a username")
            
            st.divider()  # Add visual separation
            
            # User selection section
            users = load_users()
            if users:
                selected_user = st.selectbox(
                    "Select User",
                    options=[user["name"] for user in users],
                    index=0
                )
                st.session_state.current_user = selected_user
                
                # Modified delete user button and handling
                if st.button("🗑️ Delete User", type="secondary", help="Delete selected user"):
                    success, message = delete_user(selected_user)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.warning("Please add a user first")
                return
        
        with user_tab2:
            archived_users = get_archived_users()
            if archived_users:
                st.write("Select a user to restore:")
                for archived_user in archived_users:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(archived_user)
                    with col2:
                        if st.button("Restore", key=f"restore_{archived_user}"):
                            success, message = restore_user(archived_user)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
            else:
                st.info("No archived users found")
        
        with user_tab3:
            st.write("### Backup Management")
            
            backup_method = st.radio(
                "Choose backup method:",
                ["Download File", "Copy Text"],
                horizontal=True
            )
            
            if backup_method == "Download File":
                if st.button("Download Backup"):
                    backup_content = create_backup_file()
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    st.download_button(
                        "📥 Save Backup File",
                        backup_content,
                        f"fitness_tracker_backup_{timestamp}.json",
                        "application/json",
                        help="Download a backup of all user data"
                    )
            else:  # Copy Text
                if st.button("Generate Backup Text"):
                    backup_content = create_backup_file()
                    st.code(backup_content, language="json")
                    st.info("👆 Copy this text and save it somewhere safe (like Notes or email)")
            
            # Restore section
            st.write("### Restore from Backup")
            restore_method = st.radio(
                "Choose restore method:",
                ["Upload File", "Paste Text"],
                horizontal=True
            )
            
            if restore_method == "Upload File":
                backup_file = st.file_uploader("Upload Backup File", type=['json'])
                if backup_file is not None:
                    if st.button("Restore from File"):
                        backup_content = backup_file.getvalue().decode()
                        success, message = restore_from_backup_file(backup_content)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
            else:  # Paste Text
                backup_text = st.text_area("Paste backup text here:")
                if backup_text:
                    if st.button("Restore from Text"):
                        try:
                            # Validate JSON before attempting restore
                            json.loads(backup_text)
                            success, message = restore_from_backup_file(backup_text)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                        except json.JSONDecodeError:
                            st.error("Invalid backup text. Please paste the entire backup text exactly as it was generated.")
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["Log Workout", "Exercises", "Analytics"])
    
    with tab1:
        log_workout()
    with tab2:
        manage_exercises()
    with tab3:
        show_analytics()

if __name__ == "__main__":
    main()

    # streamlit run streamlit/fitness_tracker/fitness_tracker.py