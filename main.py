from src import auth, shift_manager, child_manager, event_manager, calendar_sync, expense_manager, school_import


current_user = None # Store User object or user_id

def display_main_menu():
    print("\nFamily Planner CLI")
    print("--------------------")
    if not current_user:
        print("1. Register")
        print("2. Login")
    else:
        # Assuming User object has 'name'. If current_user is just user_id, this needs adjustment.
        user_name = current_user.name if hasattr(current_user, 'name') else current_user
        print(f"Logged in as: {user_name}")
        print("3. Add Shift")
        print("4. View My Shifts")
        print("5. Add Child")
        print("6. View My Children")
        print("7. Create Event")
        print("8. View My User Events")
        # Option 9 (View Child Events) might be too specific for this initial CLI,
        # but including for completeness based on example.
        print("9. View My Child Events (Specify Child ID)")
        print("10. Sync Google Calendar")
        print("11. Add Expense")
        print("12. View Expenses")
        print("13. Import School Calendar (.ics)")
        print("14. Logout")

    print("0. Exit")
    return input("Choose an option: ")

# --- Placeholder for handler functions ---
def handle_register():
    global current_user
    name = input("Enter name: ")
    email = input("Enter email: ")
    password = input("Enter password: ")
    user = auth.register(name, email, password)
    if user:
        current_user = user # Store the User object
        print(f"User '{user.name}' registered and logged in successfully.")
    else:
        # Error message is printed by auth.register
        pass

def handle_login():
    global current_user
    email = input("Enter email: ")
    password = input("Enter password: ")
    user = auth.login(email, password)
    if user:
        current_user = user # Store the User object
        print(f"User '{user.name}' logged in successfully.")
    else:
        # Error message is printed by auth.login
        pass

def handle_add_shift():
    if not current_user:
        print("Error: You must be logged in to add a shift.")
        return

    print("\n--- Add New Shift ---")
    # Assuming current_user is a User object with a user_id attribute
    user_id = current_user.user_id
    start_time = input("Enter shift start time (e.g., YYYY-MM-DD HH:MM): ")
    end_time = input("Enter shift end time (e.g., YYYY-MM-DD HH:MM): ")
    name = input("Enter shift name/description: ")

    shift = shift_manager.add_shift(user_id, start_time, end_time, name)
    if shift:
        print(f"Shift '{shift.name}' added successfully with ID: {shift.shift_id}")
    else:
        print("Error: Could not add shift.")

def handle_view_my_shifts():
    if not current_user:
        print("Error: You must be logged in to view shifts.")
        return

    print("\n--- Your Shifts ---")
    user_id = current_user.user_id
    shifts = shift_manager.get_user_shifts(user_id)
    if not shifts:
        print("No shifts found.")
        return
    for shift in shifts:
        print(f"ID: {shift.shift_id}, Name: {shift.name}, Start: {shift.start_time}, End: {shift.end_time}")

def handle_add_child():
    if not current_user:
        print("Error: You must be logged in to add a child.")
        return

    print("\n--- Add New Child ---")
    user_id = current_user.user_id
    name = input("Enter child's name: ")
    date_of_birth = input("Enter child's date of birth (e.g., YYYY-MM-DD): ")
    # For simplicity, school_info and custody_schedule are not taken as input here
    # They can be updated later if needed via a dedicated update function.

    child = child_manager.add_child(user_id, name, date_of_birth)
    if child:
        print(f"Child '{child.name}' added successfully with ID: {child.child_id}")
    else:
        print("Error: Could not add child.")

def handle_view_my_children():
    if not current_user:
        print("Error: You must be logged in to view children.")
        return

    print("\n--- Your Children ---")
    user_id = current_user.user_id
    children = child_manager.get_user_children(user_id)
    if not children:
        print("No children found for your account.")
        return
    for child in children:
        print(f"ID: {child.child_id}, Name: {child.name}, DOB: {child.date_of_birth}")
        # Optionally display school_info and custody_schedule if populated

def handle_create_event():
    if not current_user:
        print("Error: You must be logged in to create an event.")
        return

    print("\n--- Create New Event ---")
    title = input("Enter event title: ")
    description = input("Enter event description: ")
    start_time = input("Enter event start time (e.g., YYYY-MM-DD HH:MM): ")
    end_time = input("Enter event end time (e.g., YYYY-MM-DD HH:MM): ")

    linked_user_id = None
    linked_child_id = None

    link_choice = input("Link event to user (u), child (c), or neither (n)? [n]: ").lower()
    if link_choice == 'u':
        linked_user_id = current_user.user_id
    elif link_choice == 'c':
        # Basic: ask for child_id. Better: list children and let user pick.
        child_id_input = input("Enter child ID to link event to: ")
        # Validate child_id exists and belongs to user (optional, for robustness)
        if child_manager.get_child_details(child_id_input): # Basic check
             # Further check if child belongs to current_user
            user_children = child_manager.get_user_children(current_user.user_id)
            if any(c.child_id == child_id_input for c in user_children):
                linked_child_id = child_id_input
            else:
                print("Error: Child ID not found or does not belong to you.")
                return
        else:
            print("Error: Child ID not found.")
            return

    event = event_manager.create_event(title, description, start_time, end_time, linked_user_id, linked_child_id)
    if event:
        print(f"Event '{event.title}' created successfully with ID: {event.event_id}")
    else:
        print("Error: Could not create event.")

def handle_view_my_user_events():
    if not current_user:
        print("Error: You must be logged in to view your events.")
        return

    print("\n--- Your User Events ---")
    user_id = current_user.user_id
    events = event_manager.get_events_for_user(user_id)
    if not events:
        print("No events found linked to your user account.")
        return
    for event in events:
        print(f"ID: {event.event_id}, Title: {event.title}, Start: {event.start_time}, End: {event.end_time}, Desc: {event.description}")

def handle_view_my_child_events():
    if not current_user:
        print("Error: You must be logged in to view child events.")
        return

    print("\n--- Child Events ---")
    # Simplified: Ask for child_id.
    # Better UX: List user's children, let them pick.
    child_id_input = input("Enter child ID to view events for: ")

    # Validate child exists and belongs to user
    user_children = child_manager.get_user_children(current_user.user_id)
    if not any(c.child_id == child_id_input for c in user_children):
        print("Error: Child ID not found or does not belong to you.")
        return

    events = event_manager.get_events_for_child(child_id_input)
    if not events:
        print(f"No events found for child ID: {child_id_input}")
        return
    print(f"Events for child ID: {child_id_input}")
    for event in events:
        print(f"ID: {event.event_id}, Title: {event.title}, Start: {event.start_time}, End: {event.end_time}, Desc: {event.description}")

        
def handle_add_expense():
    if not current_user:
        print("Error: You must be logged in to add an expense.")
        return

    description = input("Expense description: ")
    amount_input = input("Amount: ")
    child_id_input = input("Child ID (optional): ")
    try:
        amount = float(amount_input)
    except ValueError:
        print("Invalid amount.")
        return

    child_id = int(child_id_input) if child_id_input else None
    exp = expense_manager.add_expense(description, amount, current_user.user_id, child_id)
    if exp:
        print("Expense added successfully.")
    else:
        print("Error adding expense.")

def handle_view_expenses():
    expenses = expense_manager.get_all_expenses()
    if not expenses:
        print("No expenses found.")
        return
    for exp in expenses:
        child_part = f" for child {exp.child_id}" if exp.child_id else ""
        print(f"ID: {exp.id} - {exp.description} - ${exp.amount:.2f}{child_part}")

def handle_sync_calendar():
    if not current_user:
        print("Error: You must be logged in to sync calendar.")
        return
    # Start OAuth flow if token is missing
    if not getattr(current_user, 'calendar_token', None):
        print("No Google credentials stored. Starting authorization...")
        calendar_sync.authorize_user(current_user.id)
    calendar_sync.sync_user_calendar(current_user.id)
    print("Calendar synced.")



def handle_import_school_calendar():
    path = input("Enter path to .ics file: ")
    imported = school_import.import_school_calendar(path)
    print(f"Imported {len(imported)} events from school calendar.")


if __name__ == "__main__":
    # Initialize the database (create tables if they don't exist)
    # This should ideally be done once. For a CLI app, doing it at startup is okay.
    # For web apps, this is often part of a startup script or migration process.
    try:
        from src.database import init_db
        init_db()
        # You might want to import models here too if init_db needs them to be defined
        # For example, if init_db() itself doesn't import them for Base.metadata.create_all()
        from src import user, shift, child, event, expense  # Ensure models are loaded for init_db
    except Exception as e:
        print(f"Error initializing database: {e}")
        # Decide if the app should exit or continue if DB init fails.
        # For this application, it's likely critical.
        # exit(1)

    while True:
        choice = display_main_menu()

        if not current_user:
            if choice == '1':
                handle_register()
            elif choice == '2':
                handle_login()
            elif choice == '0':
                print("Exiting.")
                break
            else:
                print("Invalid option or not logged in. Please try again.")
        else: # User is logged in
            if choice == '3':
                handle_add_shift()
            elif choice == '4':
                handle_view_my_shifts()
            elif choice == '5':
                handle_add_child()
            elif choice == '6':
                handle_view_my_children()
            elif choice == '7':
                handle_create_event()
            elif choice == '8':
                handle_view_my_user_events()
            elif choice == '9':
                handle_view_my_child_events()
            elif choice == '10':
              handle_sync_calendar()
            elif choice == '11':
                handle_add_expense()
            elif choice == '12':
                handle_view_expenses()
            elif choice == '13':
               handle_import_school_calendar()
            elif choice == '14':
                auth.logout() # Assuming auth.logout() is defined and handles state

               
                current_user = None
                print("Logged out successfully.")
            elif choice == '0':
                print("Exiting.")
                break
            else:
                print("Invalid option. Please try again.")
