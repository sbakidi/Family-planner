import uuid
from src.child import Child

children_storage = []  # In-memory store for Child objects
child_parent_link = {}  # In-memory store for child-parent relationships: {child_id: [user_id1, user_id2]}

def add_child(user_id, name, date_of_birth, school_info=None, custody_schedule=None):
    child_id = uuid.uuid4().hex
    new_child = Child(child_id=child_id, name=name, date_of_birth=date_of_birth)
    if school_info:
        new_child.school_info = school_info
    if custody_schedule:
        new_child.custody_schedule = custody_schedule
    
    children_storage.append(new_child)
    child_parent_link[child_id] = [user_id]
    
    return new_child

def get_child_details(child_id):
    for child in children_storage:
        if child.child_id == child_id:
            return child
    return None

def get_user_children(user_id):
    user_children_objects = []
    for child_id, parent_ids in child_parent_link.items():
        if user_id in parent_ids:
            child = get_child_details(child_id)
            if child:
                user_children_objects.append(child)
    return user_children_objects

def update_child_info(child_id, name=None, date_of_birth=None, school_info=None, custody_schedule=None):
    child = get_child_details(child_id)
    if child:
        if name is not None:
            child.name = name
        if date_of_birth is not None:
            child.date_of_birth = date_of_birth
        if school_info is not None:
            child.school_info = school_info
        if custody_schedule is not None:
            child.custody_schedule = custody_schedule
        return child  # Or True
    return None  # Or False

def remove_child(child_id):
    global children_storage, child_parent_link
    original_len_storage = len(children_storage)
    children_storage = [child for child in children_storage if child.child_id != child_id]
    
    removed_from_storage = len(children_storage) < original_len_storage
    
    if child_id in child_parent_link:
        del child_parent_link[child_id]
        removed_from_link = True
    else:
        removed_from_link = False # Or True, if we consider it "removed" if it wasn't there
        
    return removed_from_storage # Or (removed_from_storage and removed_from_link)

def add_parent_to_child(child_id, user_id):
    if child_id in child_parent_link:
        if user_id not in child_parent_link[child_id]:
            child_parent_link[child_id].append(user_id)
            return True  # Parent added
        return False  # Parent already linked
    return False  # Child ID not found
