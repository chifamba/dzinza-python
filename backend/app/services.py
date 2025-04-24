# backend/app/services.py
from urllib.parse import urljoin
from sqlalchemy.orm import Session, load_only, joinedload # Import joinedload if needed for includes
from sqlalchemy.exc import SQLAlchemyError, NoResultFound # Import NoResultFound
from sqlalchemy import or_, and_, desc, asc, Column # Import Column if needed
from typing import Optional, List, Dict, Any # Import List, Dict, Any
from datetime import date, datetime
from fastapi import Request, HTTPException # Import HTTPException

# Import models using relative paths (adjust if structure differs)
try:
    from .models import user, person, person_attribute, relationship as relationship_model, relationship_attribute, media, event, source, citation
except ImportError as e:
    logging.critical(f"Failed to import models in services: {e}")
    raise

# --- User Services ---

def get_all_users(db: Session) -> List[user.User]:
    """Retrieves all users from the database."""
    try:
        return db.query(user.User).all()
    except SQLAlchemyError as e:
        # Log the error for server-side details
        logging.error(f"Database error fetching all users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching users.")

def get_user_by_id(db: Session, user_id: int) -> user.User:
    """Retrieves a single user by their ID."""
    try:
        user_obj = db.query(user.User).filter(user.User.id == user_id).first()
        if user_obj is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user_obj
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching user ID {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching user.")

def create_user(db: Session, user_data: dict) -> user.User:
    """Creates a new user."""
    # Add validation for user_data if needed
    try:
        # Ensure password hashing is handled before this point or here
        # Example: user_data['password_hash'] = hash_function(user_data['password'])
        new_user = user.User(**user_data)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating user: {e}", exc_info=True)
        # Check for specific integrity errors (like unique username)
        if "UNIQUE constraint failed" in str(e):
             raise HTTPException(status_code=409, detail="Username already exists.")
        raise HTTPException(status_code=500, detail="Database error creating user.")

# --- Person Services ---

def get_all_people_db(db: Session, page: int = 1, page_size: int = 10, order_by: str = 'id',
                      order_direction: str = 'asc', name: Optional[str] = None,
                      gender: Optional[str] = None, birth_date: Optional[date] = None,
                      death_date: Optional[date] = None, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """Retrieves people with pagination, filtering, sorting, and field selection."""
    try:
        query = db.query(person.Person)

        # Filtering
        if name:
            # Search first_name OR last_name OR nickname
            name_filter = f"%{name}%"
            query = query.filter(or_(
                person.Person.first_name.ilike(name_filter),
                person.Person.last_name.ilike(name_filter),
                person.Person.nickname.ilike(name_filter)
            ))
        if gender:
            query = query.filter(person.Person.gender == gender)
        if birth_date:
            query = query.filter(person.Person.birth_date == birth_date)
        if death_date:
            query = query.filter(person.Person.death_date == death_date)

        # Count total items after filtering
        total_items = query.count()

        # Sorting
        valid_order_by_columns = ['id', 'first_name', 'last_name', 'gender', 'birth_date', 'death_date']
        if order_by in valid_order_by_columns:
            order_column = getattr(person.Person, order_by)
            if order_direction == 'desc':
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
        else:
            query = query.order_by(person.Person.id.asc()) # Default sort

        # Field selection (before pagination)
        if fields:
            try:
                query = query.options(load_only(*fields))
            except Exception as e:
                 logging.warning(f"Invalid fields requested for Person: {fields}. Error: {e}")
                 # Decide: ignore fields, raise 400, or proceed without load_only
                 # Proceeding without load_only for now
                 fields = None # Reset fields if invalid

        # Pagination
        offset = (page - 1) * page_size
        results = query.offset(offset).limit(page_size).all()

        # Prepare response
        total_pages = (total_items + page_size - 1) // page_size
        response_data = {
            "results": results, # Return ORM objects or dicts based on 'fields'
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

        # If specific fields were requested, convert results to dictionaries
        # Note: This happens *after* pagination query
        if fields:
             response_data["results"] = [
                 {field: getattr(item, field) for field in fields if hasattr(item, field)}
                 for item in results
             ]

        return response_data

    except SQLAlchemyError as e:
        logging.error(f"Database error fetching people: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching people.")
    except Exception as e: # Catch potential errors in field selection/processing
        logging.error(f"Error processing people request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing people request.")


def get_person_by_id_db(db: Session, person_id: int, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """Retrieves a single person by ID, optionally selecting specific fields."""
    try:
        query = db.query(person.Person).filter(person.Person.id == person_id)

        if fields:
            try:
                query = query.options(load_only(*fields))
            except Exception as e:
                 logging.warning(f"Invalid fields requested for Person ID {person_id}: {fields}. Error: {e}")
                 fields = None # Reset fields if invalid

        person_obj = query.first()

        if person_obj is None:
            raise HTTPException(status_code=404, detail="Person not found")

        # Convert to dictionary, handling selected fields
        if fields:
            response_data = {field: getattr(person_obj, field) for field in fields if hasattr(person_obj, field)}
        else:
            # Convert full object to dict, remove SQLAlchemy state
            response_data = person_obj.to_dict() # Assuming Person has to_dict()
            if "_sa_instance_state" in response_data:
                 del response_data["_sa_instance_state"]

        # Add HATEOAS links (optional)
        # response_data["_links"] = {
        #     "self": f"/api/people/{person_id}",
        #     "relationships": f"/api/relationships?person_id={person_id}",
        #     "attributes": f"/api/person_attributes?person_id={person_id}",
        # }
        return response_data

    except NoResultFound: # Should be caught by query.first() returning None
         raise HTTPException(status_code=404, detail="Person not found")
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching person ID {person_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching person.")
    except Exception as e:
        logging.error(f"Error processing get person request for ID {person_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing person request.")

def create_person_db(db: Session, person_data: dict) -> person.Person:
    """Creates a new person in the database."""
    # Add validation if not done in the route handler
    try:
        new_person = person.Person(**person_data)
        db.add(new_person)
        db.commit()
        db.refresh(new_person)
        return new_person
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating person: {e}", exc_info=True)
        if "UNIQUE constraint failed" in str(e) or "duplicate key value violates unique constraint" in str(e):
             raise HTTPException(status_code=409, detail="Person creation conflict (e.g., duplicate identifier).")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e):
             raise HTTPException(status_code=400, detail=f"Missing required field for person: {e}")
        raise HTTPException(status_code=500, detail="Database error creating person.")

# --- Add update_person_db, delete_person_db similarly ---

# --- Relationship Services ---

def get_all_relationships(db: Session, request: Request, page: int = 1, page_size: int = 10,
                          order_by: str = 'id', order_direction: str = 'asc',
                          type: Optional[str] = None, person1_id: Optional[int] = None,
                          person2_id: Optional[int] = None, fields: Optional[List[str]] = None,
                          include_person1: bool = False, include_person2: bool = False) -> Dict[str, Any]:
    """Retrieves relationships with pagination, filtering, sorting, field selection, and optional includes."""
    try:
        query = db.query(relationship_model.Relationship) # Use alias

        # Filtering
        if type:
            query = query.filter(relationship_model.Relationship.rel_type == type)
        if person1_id:
            query = query.filter(relationship_model.Relationship.person1_id == person1_id)
        if person2_id:
            query = query.filter(relationship_model.Relationship.person2_id == person2_id)

        total_items = query.count()

        # Sorting
        valid_order_by_columns = ['id', 'rel_type', 'person1_id', 'person2_id'] # Use model field names
        if order_by in valid_order_by_columns:
            order_column = getattr(relationship_model.Relationship, order_by)
            query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))
        else:
            query = query.order_by(relationship_model.Relationship.id.asc())

        # Includes (before pagination and field selection)
        if include_person1:
            query = query.options(joinedload(relationship_model.Relationship.person1))
        if include_person2:
            query = query.options(joinedload(relationship_model.Relationship.person2))

        # Field selection (before pagination)
        if fields:
            # Ensure primary/foreign keys are included if needed for includes/links
            required_fields = {'id', 'person1_id', 'person2_id'}
            final_fields = list(set(fields) | required_fields)
            try:
                query = query.options(load_only(*final_fields))
            except Exception as e:
                 logging.warning(f"Invalid fields requested for Relationship: {fields}. Error: {e}")
                 fields = None # Reset fields

        # Pagination
        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        # Prepare response data
        results_list = []
        base_url = str(request.base_url)
        for item in results_orm:
            if fields:
                item_data = {field: getattr(item, field) for field in final_fields if hasattr(item, field)}
            else:
                item_data = item.to_dict() # Assuming Relationship has to_dict()
                if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

            # Add links
            item_data["_links"] = {
                "self": urljoin(base_url, f"/api/relationships/{item.id}"),
                "person1": urljoin(base_url, f"/api/people/{item.person1_id}"),
                "person2": urljoin(base_url, f"/api/people/{item.person2_id}"),
            }

            # Add included data
            if include_person1 and hasattr(item, 'person1') and item.person1:
                item_data["person1"] = item.person1.to_dict() # Assuming Person has to_dict
                if "_sa_instance_state" in item_data["person1"]: del item_data["person1"]["_sa_instance_state"]
            if include_person2 and hasattr(item, 'person2') and item.person2:
                item_data["person2"] = item.person2.to_dict()
                if "_sa_instance_state" in item_data["person2"]: del item_data["person2"]["_sa_instance_state"]

            results_list.append(item_data)

        total_pages = (total_items + page_size - 1) // page_size
        return {
            "results": results_list,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching relationships: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching relationships.")
    except Exception as e:
        logging.error(f"Error processing relationships request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing relationships request.")


# --- Add get_relationship_by_id, create_relationship, update_relationship, delete_relationship ---
# --- Remember to handle includes and field selection in get_relationship_by_id ---

# --- Relationship Attribute Services ---
# --- Implement similarly to Person Attribute Services, using relationship_attribute model ---

# --- Person Attribute Services ---

def get_all_person_attributes(db: Session, page: int = 1, page_size: int = 10,
                              order_by: str = 'id', order_direction: str = 'asc',
                              key: Optional[str] = None, value: Optional[str] = None,
                              person_id: Optional[int] = None, # Added person_id filter
                              fields: Optional[List[str]] = None,
                              include_person: bool = False) -> Dict[str, Any]:
    """Retrieves person attributes with pagination, filtering, sorting, field selection, and optional includes."""
    try:
        query = db.query(person_attribute.PersonAttribute)

        # Filtering
        if key:
            query = query.filter(person_attribute.PersonAttribute.key.ilike(f"%{key}%"))
        if value:
            query = query.filter(person_attribute.PersonAttribute.value.ilike(f"%{value}%"))
        if person_id:
            query = query.filter(person_attribute.PersonAttribute.person_id == person_id)

        total_items = query.count()

        # Sorting
        valid_order_by_columns = ['id', 'key', 'value', 'person_id']
        if order_by in valid_order_by_columns:
            order_column = getattr(person_attribute.PersonAttribute, order_by)
            query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))
        else:
            query = query.order_by(person_attribute.PersonAttribute.id.asc())

        # Includes
        if include_person:
            query = query.options(joinedload(person_attribute.PersonAttribute.person))

        # Field selection
        if fields:
             required_fields = {'id', 'person_id'} # Keep keys needed for links/includes
             final_fields = list(set(fields) | required_fields)
             try:
                 query = query.options(load_only(*final_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for PersonAttribute: {fields}. Error: {e}")
                 fields = None # Reset

        # Pagination
        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        # Prepare response
        results_list = []
        # base_url = str(request.base_url) # Need request object if generating links
        for item in results_orm:
            if fields:
                item_data = {field: getattr(item, field) for field in final_fields if hasattr(item, field)}
            else:
                item_data = item.to_dict() # Assuming model has to_dict()
                if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

            # Add links (requires request object or base URL)
            # item_data["_links"] = {"person": urljoin(base_url, f"/api/people/{item.person_id}")}

            # Add included data
            if include_person and hasattr(item, 'person') and item.person:
                item_data["person"] = item.person.to_dict()
                if "_sa_instance_state" in item_data["person"]: del item_data["person"]["_sa_instance_state"]

            results_list.append(item_data)

        total_pages = (total_items + page_size - 1) // page_size
        return {
            "results": results_list,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching person attributes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching person attributes.")
    except Exception as e:
        logging.error(f"Error processing person attributes request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing person attributes request.")


def get_person_attribute(db: Session, person_attribute_id: int,
                         fields: Optional[List[str]] = None,
                         include_person: bool = False) -> Optional[Dict[str, Any]]:
    """Retrieves a single person attribute by ID."""
    try:
        query = db.query(person_attribute.PersonAttribute).filter(person_attribute.PersonAttribute.id == person_attribute_id)

        if include_person:
            query = query.options(joinedload(person_attribute.PersonAttribute.person))

        if fields:
             required_fields = {'id', 'person_id'}
             final_fields = list(set(fields) | required_fields)
             try:
                 query = query.options(load_only(*final_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for PersonAttribute ID {person_attribute_id}: {fields}. Error: {e}")
                 fields = None # Reset

        attr_obj = query.first()

        if attr_obj is None:
            # Return None instead of raising 404 here, let route handler do it
            return None

        # Prepare response data
        if fields:
            item_data = {field: getattr(attr_obj, field) for field in final_fields if hasattr(attr_obj, field)}
        else:
            item_data = attr_obj.to_dict() # Assuming model has to_dict()
            if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

        # Add links
        # item_data["_links"] = {"person": f"/api/people/{attr_obj.person_id}"}

        # Add included data
        if include_person and hasattr(attr_obj, 'person') and attr_obj.person:
            item_data["person"] = attr_obj.person.to_dict()
            if "_sa_instance_state" in item_data["person"]: del item_data["person"]["_sa_instance_state"]

        return item_data

    except SQLAlchemyError as e:
        logging.error(f"Database error fetching person attribute ID {person_attribute_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching person attribute.")
    except Exception as e:
        logging.error(f"Error processing get person attribute request for ID {person_attribute_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing person attribute request.")


# --- Add create, update, delete for person attributes ---

# --- Media, Event, Source, Citation Services ---
# --- Implement similarly, following the pattern for pagination, filtering, sorting, field selection, includes ---

# --- Tree Traversal Services ---
# These functions likely need adaptation to work directly with SQLAlchemy queries
# instead of in-memory dicts, or they might fetch data first and then process.

def get_ancestors(db: Session, person_id: int, depth: int) -> List[person.Person]:
    """Retrieves ancestors using SQLAlchemy (example - needs recursive query or iterative approach)."""
    # This is a placeholder - actual implementation requires recursive CTEs or iterative queries
    logging.warning("get_ancestors service function needs implementation using SQLAlchemy.")
    # Example iterative approach (limited depth):
    ancestors = []
    queue = [(person_id, 0)]
    visited = {person_id}

    while queue:
        current_id, current_depth = queue.pop(0)
        if current_depth >= depth:
            continue

        # Find parents (Person B where Relationship is A (parent) -> B (child))
        parent_rels = db.query(relationship_model.Relationship).filter(
            relationship_model.Relationship.person2_id == current_id,
            relationship_model.Relationship.rel_type == 'parent' # Assuming 'parent' means person1 is parent of person2
        ).all()

        for rel in parent_rels:
            parent_id = rel.person1_id
            if parent_id not in visited:
                parent_obj = db.query(person.Person).get(parent_id)
                if parent_obj:
                    ancestors.append(parent_obj)
                    visited.add(parent_id)
                    queue.append((parent_id, current_depth + 1))
    return ancestors

# --- Implement get_descendants, get_extended_family, get_related, get_partial_tree, get_branch similarly ---

# --- Search Service ---
def search_people(db: Session, name: Optional[str] = None, birth_date: Optional[date] = None,
                  death_date: Optional[date] = None, gender: Optional[str] = None,
                  place_of_birth: Optional[str] = None, place_of_death: Optional[str] = None,
                  notes: Optional[str] = None, attribute_key: Optional[str] = None,
                  attribute_value: Optional[str] = None) -> List[person.Person]:
    """Searches people based on multiple criteria."""
    try:
        query = db.query(person.Person)

        if name:
            name_filter = f"%{name}%"
            query = query.filter(or_(
                person.Person.first_name.ilike(name_filter),
                person.Person.last_name.ilike(name_filter),
                person.Person.nickname.ilike(name_filter)
            ))
        if birth_date:
            query = query.filter(person.Person.birth_date == birth_date)
        if death_date:
            query = query.filter(person.Person.death_date == death_date)
        if gender:
            query = query.filter(person.Person.gender == gender)
        if place_of_birth:
            query = query.filter(person.Person.place_of_birth.ilike(f"%{place_of_birth}%"))
        if place_of_death:
            query = query.filter(person.Person.place_of_death.ilike(f"%{place_of_death}%"))
        if notes:
            query = query.filter(person.Person.notes.ilike(f"%{notes}%"))

        # Join with attributes if searching by attribute
        if attribute_key or attribute_value:
            query = query.join(person.Person.attributes) # Assumes relationship named 'attributes'
            if attribute_key:
                query = query.filter(person_attribute.PersonAttribute.key == attribute_key)
            if attribute_value:
                query = query.filter(person_attribute.PersonAttribute.value.ilike(f"%{attribute_value}%"))
            # Ensure distinct results if joining
            query = query.distinct()

        return query.all()
    except SQLAlchemyError as e:
        logging.error(f"Database error during person search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error during search.")


def get_person_relationships_and_attributes(db: Session, person_id: int) -> Dict[str, Any]:
    """Retrieves relationships and attributes for a specific person."""
    try:
        # Fetch the person to ensure they exist
        person_obj = db.query(person.Person).filter(person.Person.id == person_id).first()
        if not person_obj:
            raise HTTPException(status_code=404, detail="Person not found")

        # Fetch attributes for the person
        person_attrs = db.query(person_attribute.PersonAttribute)\
                         .filter(person_attribute.PersonAttribute.person_id == person_id)\
                         .all()

        # Fetch relationships where the person is either person1 or person2
        person_rels_orm = db.query(relationship_model.Relationship)\
                            .filter(or_(relationship_model.Relationship.person1_id == person_id,
                                        relationship_model.Relationship.person2_id == person_id))\
                            .options(joinedload(relationship_model.Relationship.attributes)) # Include relationship attributes
                            .all()

        # Format the results
        person_attributes_data = [attr.to_dict() for attr in person_attrs] # Assuming to_dict exists
        relationships_data = []
        for rel in person_rels_orm:
            rel_data = rel.to_dict() # Assuming to_dict exists
            # Ensure relationship attributes are included and formatted
            rel_data['attributes'] = [rel_attr.to_dict() for rel_attr in rel.attributes] # Assuming to_dict exists
            relationships_data.append(rel_data)

        return {
            "person_attributes": person_attributes_data,
            "relationships": relationships_data
        }
    except NoResultFound: # Should be caught by the initial person query
        raise HTTPException(status_code=404, detail="Person not found")
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching relationships/attributes for person {person_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching relationships/attributes.")

# --- Fix potential indentation error at the end of the original file ---
# (Removed the specific line number as it might change, ensure last function is correctly indented)

