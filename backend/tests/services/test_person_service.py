import pytest
import uuid
from sqlalchemy.orm import Session
from werkzeug.exceptions import NotFound, BadRequest

from models import Person, Tree, User, PersonTreeAssociation, ActivityLog
from services.person_service import (
    create_person_db,
    get_all_people_db,
    get_person_db,
    update_person_db,
    delete_person_db,
    update_person_order_db
)
from services.tree_service import create_tree_db # To create a tree for context
from services.user_service import get_or_create_user # To create a user for created_by

# Helper to create a user
def create_test_user(db: Session, id_suffix: str = "") -> User:
    user_data = {
        "username": f"testuser_person_svc{id_suffix}",
        "email": f"testuser_person_svc{id_suffix}@example.com",
        "password": "password123"
    }
    user, _ = get_or_create_user(db, user_data["username"], user_data["email"], user_data["password"])
    return user

# Helper to create a tree
def create_test_tree(db: Session, user: User, id_suffix: str = "") -> Tree:
    tree_data = {"name": f"Test Tree PersonSvc{id_suffix}", "created_by": user.id}
    # create_tree_db returns a dict, we need the Tree object
    tree_dict = create_tree_db(db, user_id=user.id, tree_data={"name": tree_data["name"]})
    return db.query(Tree).filter_by(id=uuid.UUID(tree_dict["id"])).one()

# Helper to create a person and associate with a tree
def create_associated_person(db: Session, user: User, tree: Tree, first_name: str, last_name: str, display_order: int = None) -> Person:
    person_data = {
        "first_name": first_name,
        "last_name": last_name,
        "is_living": True,
    }
    if display_order is not None:
        person_data["display_order"] = display_order

    person_dict = create_person_db(db, user_id=user.id, tree_id=tree.id, person_data=person_data)
    return db.query(Person).filter_by(id=uuid.UUID(person_dict["id"])).one()


@pytest.fixture(scope="function")
def setup_teardown_db(db_session: Session):
    # Clean up relevant tables before each test
    db_session.query(ActivityLog).delete()
    db_session.query(PersonTreeAssociation).delete()
    db_session.query(Person).delete()
    db_session.query(Tree).delete()
    db_session.query(User).delete()
    db_session.commit()
    yield db_session
    db_session.rollback() # Ensure rollback after each test

def test_create_person_db_assigns_display_order(setup_teardown_db: Session):
    db = setup_teardown_db
    user = create_test_user(db, "do_create")
    tree = create_test_tree(db, user, "do_create")

    # Person 1: display_order not provided
    person1_data = {"first_name": "Alice", "last_name": "Smith", "is_living": True}
    person1_dict = create_person_db(db, user_id=user.id, tree_id=tree.id, person_data=person1_data)
    person1 = db.query(Person).filter_by(id=uuid.UUID(person1_dict["id"])).one()
    assert person1.display_order == 1 # First person, service should assign 1 (max_order or 0) + 1

    # Person 2: display_order provided
    person2_data = {"first_name": "Bob", "last_name": "Johnson", "is_living": True, "display_order": 5}
    person2_dict = create_person_db(db, user_id=user.id, tree_id=tree.id, person_data=person2_data)
    person2 = db.query(Person).filter_by(id=uuid.UUID(person2_dict["id"])).one()
    assert person2.display_order == 5

    # Person 3: display_order not provided, should be max existing (5) + 1 = 6
    person3_data = {"first_name": "Charlie", "last_name": "Brown", "is_living": True}
    person3_dict = create_person_db(db, user_id=user.id, tree_id=tree.id, person_data=person3_data)
    person3 = db.query(Person).filter_by(id=uuid.UUID(person3_dict["id"])).one()
    assert person3.display_order == 6

    # Check activity log for person creation
    log_entry = db.query(ActivityLog).filter_by(entity_id=person1.id, action_type="CREATE_PERSON").first()
    assert log_entry is not None
    assert log_entry.tree_id == tree.id

def test_get_all_people_db_sorts_by_display_order(setup_teardown_db: Session):
    db = setup_teardown_db
    user = create_test_user(db, "do_getall")
    tree = create_test_tree(db, user, "do_getall")

    create_associated_person(db, user, tree, "Charlie", "Xylophone", display_order=2)
    create_associated_person(db, user, tree, "Alice", "Yankee", display_order=0)
    create_associated_person(db, user, tree, "Bob", "Zulu", display_order=1)

    # Default sort is by display_order asc
    result = get_all_people_db(db, tree_id=tree.id)
    person_names_ordered = [p["first_name"] for p in result["items"]]
    assert person_names_ordered == ["Alice", "Bob", "Charlie"]

    # Test explicit sort by display_order desc
    result_desc = get_all_people_db(db, tree_id=tree.id, sort_order="desc")
    person_names_ordered_desc = [p["first_name"] for p in result_desc["items"]]
    assert person_names_ordered_desc == ["Charlie", "Bob", "Alice"]

def test_update_person_order_db_success(setup_teardown_db: Session):
    db = setup_teardown_db
    user = create_test_user(db, "do_update_order")
    tree = create_test_tree(db, user, "do_update_order")

    p1 = create_associated_person(db, user, tree, "P1", "LN1", display_order=0)
    p2 = create_associated_person(db, user, tree, "P2", "LN2", display_order=1)
    p3 = create_associated_person(db, user, tree, "P3", "LN3", display_order=2)

    new_order_data = [
        {"id": str(p3.id), "display_order": 0}, # P3 moves to start
        {"id": str(p1.id), "display_order": 1}, # P1 moves to middle
        {"id": str(p2.id), "display_order": 2}, # P2 moves to end
    ]

    success = update_person_order_db(db, tree_id=tree.id, persons_data=new_order_data, actor_user_id=user.id)
    assert success is True

    db.refresh(p1)
    db.refresh(p2)
    db.refresh(p3)

    assert p3.display_order == 0
    assert p1.display_order == 1
    assert p2.display_order == 2

    # Check activity log
    log_entry = db.query(ActivityLog).filter_by(entity_id=tree.id, action_type="UPDATE_PERSON_ORDER").first()
    assert log_entry is not None
    assert log_entry.actor_user_id == user.id
    assert len(log_entry.details["updated_persons_summary"]) == 3


def test_update_person_order_db_no_actual_change(setup_teardown_db: Session):
    db = setup_teardown_db
    user = create_test_user(db, "do_no_change")
    tree = create_test_tree(db, user, "do_no_change")
    p1 = create_associated_person(db, user, tree, "P1", "LN1", display_order=0)

    new_order_data = [{"id": str(p1.id), "display_order": 0}] # Same order
    success = update_person_order_db(db, tree_id=tree.id, persons_data=new_order_data, actor_user_id=user.id)
    assert success is True
    # Verify no specific "UPDATE_PERSON_ORDER" log if no changes were made, or that it indicates no changes.
    # The current service logs even if no changes, but details list will be empty.
    log_entry = db.query(ActivityLog).filter_by(entity_id=tree.id, action_type="UPDATE_PERSON_ORDER").first()
    assert log_entry is not None # Service logs "No actual order changes detected."
    assert log_entry.details["message"] == "Updated display order for 0 persons."


def test_update_person_order_db_invalid_person_id(setup_teardown_db: Session):
    db = setup_teardown_db
    user = create_test_user(db, "do_invalid_id")
    tree = create_test_tree(db, user, "do_invalid_id")
    p1 = create_associated_person(db, user, tree, "P1", "LN1", display_order=0)

    invalid_person_id = uuid.uuid4()
    new_order_data = [
        {"id": str(p1.id), "display_order": 1},
        {"id": str(invalid_person_id), "display_order": 0},
    ]

    with pytest.raises(BadRequest) as excinfo: # Service uses abort(400) which raises BadRequest
        update_person_order_db(db, tree_id=tree.id, persons_data=new_order_data, actor_user_id=user.id)
    assert "One or more persons not found or not associated with the tree" in str(excinfo.value.description)

def test_update_person_order_db_person_from_different_tree(setup_teardown_db: Session):
    db = setup_teardown_db
    user = create_test_user(db, "do_diff_tree")
    tree1 = create_test_tree(db, user, "do_dt1")
    tree2 = create_test_tree(db, user, "do_dt2")

    p1_tree1 = create_associated_person(db, user, tree1, "P1T1", "LN", display_order=0)
    p2_tree2 = create_associated_person(db, user, tree2, "P2T2", "LN", display_order=0) # Belongs to tree2

    # Attempt to include p2_tree2 in an order update for tree1
    new_order_data = [
        {"id": str(p1_tree1.id), "display_order": 1},
        {"id": str(p2_tree2.id), "display_order": 0}, # This person is not in tree1
    ]

    with pytest.raises(BadRequest) as excinfo:
        update_person_order_db(db, tree_id=tree1.id, persons_data=new_order_data, actor_user_id=user.id)
    assert "One or more persons not found or not associated with the tree" in str(excinfo.value.description)

def test_update_person_order_db_empty_list(setup_teardown_db: Session):
    db = setup_teardown_db
    user = create_test_user(db, "do_empty")
    tree = create_test_tree(db, user, "do_empty")

    success = update_person_order_db(db, tree_id=tree.id, persons_data=[], actor_user_id=user.id)
    assert success is True # Should succeed with no action
    log_entry = db.query(ActivityLog).filter_by(entity_id=tree.id, action_type="UPDATE_PERSON_ORDER").first()
    assert log_entry is None # No log if no data provided, as per current service logic

def test_update_person_order_db_missing_id_or_order_in_data(setup_teardown_db: Session):
    db = setup_teardown_db
    user = create_test_user(db, "do_missing_data")
    tree = create_test_tree(db, user, "do_missing_data")
    p1 = create_associated_person(db, user, tree, "P1", "LN1", display_order=0)

    # Case 1: Missing display_order
    order_data_missing_order = [{"id": str(p1.id)}]
    # Service skips items with missing id or display_order, so this results in no changes.
    # It doesn't raise an error directly for this, but logs a warning and effectively does nothing for that item.
    success = update_person_order_db(db, tree_id=tree.id, persons_data=order_data_missing_order, actor_user_id=user.id)
    assert success is True
    log_update = db.query(ActivityLog).filter_by(action_type="UPDATE_PERSON_ORDER").first()
    assert log_update.details['message'] == 'Updated display order for 0 persons.'


    # Case 2: Missing id (though id is used to fetch, so this item would be unmatchable)
    # The service currently filters by valid IDs first. If an item has no 'id', it won't be in person_ids_to_update.
    # If it has an 'id' that's invalid, it's caught by the "person not found" check.
    # If an item in persons_data is like `{"display_order": 0}` (no id), it's skipped.
    order_data_missing_id = [{"display_order": 0}]
    success_missing_id = update_person_order_db(db, tree_id=tree.id, persons_data=order_data_missing_id, actor_user_id=user.id)
    assert success_missing_id is True
    # This would also result in "0 persons" updated as the item with missing id is skipped.
    # To be more precise, we can check the log again or ensure p1's order is unchanged.
    db.refresh(p1)
    assert p1.display_order == 0

    # Case 3: Empty dictionary in list
    order_data_empty_dict = [{}]
    success_empty_dict = update_person_order_db(db, tree_id=tree.id, persons_data=order_data_empty_dict, actor_user_id=user.id)
    assert success_empty_dict is True
    db.refresh(p1)
    assert p1.display_order == 0


# Minimal test for get_person_db and update_person_db to ensure they exist for other tests
def test_get_and_update_person_exist(setup_teardown_db: Session):
    db = setup_teardown_db
    user = create_test_user(db, "do_get_update_exist")
    tree = create_test_tree(db, user, "do_get_update_exist")
    person = create_associated_person(db, user, tree, "Test", "Person")

    fetched_person = get_person_db(db, person_id=person.id, tree_id=tree.id)
    assert fetched_person["id"] == str(person.id)

    update_data = {"first_name": "UpdatedName", "display_order": 10} # Include display_order
    updated_person = update_person_db(db, person_id=person.id, tree_id=tree.id, person_data=update_data, actor_user_id=user.id)
    assert updated_person["first_name"] == "UpdatedName"
    assert updated_person["display_order"] == 10


def test_delete_person_exist(setup_teardown_db: Session):
    db = setup_teardown_db
    user = create_test_user(db, "do_delete_exist")
    tree = create_test_tree(db, user, "do_delete_exist")
    person = create_associated_person(db, user, tree, "Test", "DeleteMe")

    success = delete_person_db(db, person_id=person.id, tree_id=tree.id, actor_user_id=user.id)
    assert success is True
    with pytest.raises(NotFound): # Expect NotFound after deletion
        get_person_db(db, person_id=person.id, tree_id=tree.id)

    # Check activity log for person deletion
    log_entry = db.query(ActivityLog).filter_by(entity_id=person.id, action_type="DELETE_PERSON").first()
    assert log_entry is not None
    assert log_entry.tree_id == tree.id
    assert log_entry.actor_user_id == user.id
    assert log_entry.previous_state["first_name"] == "Test"
