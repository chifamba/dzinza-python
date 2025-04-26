# backend/app/services.py
import logging
from urllib.parse import urljoin
from sqlalchemy.orm import Session, load_only, joinedload
from sqlalchemy.exc import SQLAlchemyError, NoResultFound, IntegrityError
from sqlalchemy import or_, and_, desc, asc
from typing import Optional, List, Dict, Any
from datetime import date
# Using Flask's abort for error handling
from flask import abort, request # Import Flask's request object for get_all_relationships links

# Import models using relative paths
try:
    from app.models.user import User
    from app.models.person import Person
    from app.models.person_attribute import PersonAttribute
    from app.models.relationship import Relationship as RelationshipModel
    from app.models.relationship_attribute import RelationshipAttribute
    from app.models.media import Media
    from app.models.event import Event # Ensure Event model is correctly defined and imported
    from app.models.source import Source # Ensure Source model is correctly defined and imported
    from app.models.citation import Citation # Ensure Citation model is correctly defined and imported
    from app.models.base import Base # Import Base if needed for metadata (though typically handled in main/app)
except ImportError as e:
    logging.critical(f"Failed to import models in services: {e}")
    raise

# --- User Services (Already Implemented) ---
# These functions seem to have basic implementation already.

def get_all_users(db: Session) -> List[User]:
    """Retrieves all users from the database."""
    try:
        return db.query(User).all()
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching all users: {e}", exc_info=True)
        abort(500, description="Database error fetching users.")

def get_user_by_id(db: Session, user_id: int) -> User:
    """Retrieves a single user by their ID."""
    try:
        user_obj = db.query(User).filter(User.id == user_id).first()
        if user_obj is None:
            abort(404, description="User not found")
        return user_obj
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching user ID {user_id}: {e}", exc_info=True)
        abort(500, description="Database error fetching user.")

def create_user(db: Session, user_data: dict) -> User:
    """Creates a new user."""
    try:
        # Password hashing should be handled elsewhere, ideally before calling this service
        new_user = User(**user_data)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating user: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Username already exists.")
        abort(500, description="Database error creating user.")

# --- Person Services (get_all and get_by_id implemented, create implemented) ---
# Added update and delete

def get_all_people_db(db: Session, page: int = 1, page_size: int = 10, order_by: str = 'id',
                      order_direction: str = 'asc', name: Optional[str] = None,
                      gender: Optional[str] = None, birth_date: Optional[date] = None,
                      death_date: Optional[date] = None, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """Retrieves people with pagination, filtering, sorting, and field selection."""
    try:
        query = db.query(Person)

        # Filtering
        if name:
            name_filter = f"%{name}%"
            query = query.filter(or_(
                Person.first_name.ilike(name_filter),
                Person.last_name.ilike(name_filter),
                Person.nickname.ilike(name_filter)
            ))
        if gender:
            query = query.filter(Person.gender == gender)
        if birth_date:
            query = query.filter(Person.birth_date == birth_date)
        if death_date:
            query = query.filter(Person.death_date == death_date)

        total_items = query.count()

        # Sorting
        valid_order_by_columns = ['id', 'first_name', 'last_name', 'gender', 'birth_date', 'death_date']
        sort_column_name = order_by if order_by in valid_order_by_columns else 'id'
        order_column = getattr(Person, sort_column_name)
        query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))

        # Field selection
        final_fields = None
        if fields:
            try:
                required_fields = {'id'}
                final_fields = list(set(fields) | required_fields)
                query = query.options(load_only(*final_fields))
            except Exception as e:
                 logging.warning(f"Invalid fields requested for Person: {fields}. Error: {e}. Ignoring.")
                 final_fields = None # Ignore field selection on error

        # Pagination
        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        # Prepare response
        results_list = []
        for item in results_orm:
             if final_fields:
                 item_data = {field: getattr(item, field, None) for field in final_fields}
             else:
                 item_data = item.to_dict() # Assuming to_dict exists on models
                 if "_sa_instance_state" in item_data:
                     del item_data["_sa_instance_state"]
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
        logging.error(f"Database error fetching people: {e}", exc_info=True)
        abort(500, description="Database error fetching people.")
    except Exception as e:
        logging.error(f"Error processing people request: {e}", exc_info=True)
        abort(500, description="Error processing people request.")


def get_person_by_id_db(db: Session, person_id: int, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """Retrieves a single person by ID, optionally selecting specific fields."""
    try:
        query = db.query(Person).filter(Person.id == person_id)

        final_fields = None
        if fields:
            try:
                required_fields = {'id'}
                final_fields = list(set(fields) | required_fields)
                query = query.options(load_only(*final_fields))
            except Exception as e:
                 logging.warning(f"Invalid fields requested for Person ID {person_id}: {fields}. Error: {e}. Ignoring.")
                 final_fields = None

        person_obj = query.first()

        if person_obj is None:
            abort(404, description="Person not found")

        if final_fields:
            response_data = {field: getattr(person_obj, field, None) for field in final_fields}
        else:
            response_data = person_obj.to_dict()
            if "_sa_instance_state" in response_data:
                 del response_data["_sa_instance_state"]

        return response_data

    except NoResultFound: # This is actually handled by .first() returning None, but kept for clarity/safety
         abort(404, description="Person not found")
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching person ID {person_id}: {e}", exc_info=True)
        abort(500, description="Database error fetching person.")
    except Exception as e:
        logging.error(f"Error processing get person request for ID {person_id}: {e}", exc_info=True)
        abort(500, description="Error processing person request.")

def create_person_db(db: Session, person_data: dict) -> Dict[str, Any]: # Changed return type to Dict for consistency
    """Creates a new person in the database."""
    try:
        new_person = Person(**person_data)
        db.add(new_person)
        db.commit()
        db.refresh(new_person)
        return new_person.to_dict() # Return dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating person: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Person creation conflict.")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e):
             abort(400, description=f"Missing required field for person: {e}")
        abort(500, description="Database error creating person.")

def update_person_db(db: Session, person_id: int, person_data: dict) -> Optional[Dict[str, Any]]:
    """Updates an existing person in the database."""
    try:
        person_obj = db.query(Person).filter(Person.id == person_id).first()
        if person_obj is None:
            abort(404, description="Person not found")

        # Update attributes from the provided data
        for key, value in person_data.items():
            if hasattr(person_obj, key):
                setattr(person_obj, key, value)

        db.commit()
        db.refresh(person_obj)
        return person_obj.to_dict() # Return updated dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error updating person {person_id}: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Person update conflict.")
        abort(500, description="Database error updating person.")
    except Exception as e:
        logging.error(f"Error processing update person request for ID {person_id}: {e}", exc_info=True)
        abort(500, description="Error processing person update request.")


def delete_person_db(db: Session, person_id: int) -> bool:
    """Deletes a person from the database."""
    try:
        person_obj = db.query(Person).filter(Person.id == person_id).first()
        if person_obj is None:
            abort(404, description="Person not found")

        db.delete(person_obj)
        db.commit()
        return True # Indicate successful deletion
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error deleting person {person_id}: {e}", exc_info=True)
        abort(500, description="Database error deleting person.")
    except Exception as e:
        logging.error(f"Error processing delete person request for ID {person_id}: {e}", exc_info=True)
        abort(500, description="Error processing person deletion request.")


# --- Relationship Services (get_all implemented) ---
# Added get_by_id, create, update, delete

# Removed 'request: Request' from signature, using Flask's global request object
def get_all_relationships(db: Session, page: int = 1, page_size: int = 10,
                          order_by: str = 'id', order_direction: str = 'asc',
                          type: Optional[str] = None, person1_id: Optional[int] = None,
                          person2_id: Optional[int] = None, fields: Optional[List[str]] = None,
                          include_person1: bool = False, include_person2: bool = False) -> Dict[str, Any]:
    """Retrieves relationships with pagination, filtering, sorting, field selection, and optional includes."""
    try:
        query = db.query(RelationshipModel)

        # Filtering
        if type:
            query = query.filter(RelationshipModel.rel_type == type)
        if person1_id:
            query = query.filter(RelationshipModel.person1_id == person1_id)
        if person2_id:
            query = query.filter(RelationshipModel.person2_id == person2_id)

        total_items = query.count()

        # Sorting
        valid_order_by_columns = ['id', 'rel_type', 'person1_id', 'person2_id']
        sort_column_name = order_by if order_by in valid_order_by_columns else 'id'
        order_column = getattr(RelationshipModel, sort_column_name)
        query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))

        # Includes
        load_options = []
        if include_person1:
            load_options.append(joinedload(RelationshipModel.person1))
        if include_person2:
            load_options.append(joinedload(RelationshipModel.person2))
        if load_options:
             query = query.options(*load_options)

        # Field selection
        final_fields = None
        if fields:
            required_fields = {'id', 'person1_id', 'person2_id'}
            final_fields = list(set(fields) | required_fields)
            try:
                # Apply load_only only to the RelationshipModel's columns
                rel_model_fields = [f for f in final_fields if hasattr(RelationshipModel, f)]
                if rel_model_fields:
                    query = query.options(load_only(*rel_model_fields))
            except Exception as e:
                 logging.warning(f"Invalid fields requested for Relationship: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None # Ignore field selection on error


        # Pagination
        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        # Prepare response data
        results_list = []
        # Use Flask's request.url_root to get the base URL
        # Check if request context is available (might not be in some service calls)
        base_url = request.url_root if request else ""


        for item in results_orm:
            if final_fields:
                # Manually construct dict if fields were selected, getting data from loaded objects
                item_data = {field: getattr(item, field, None) for field in final_fields if hasattr(item, field)}
                # Include included relationship fields if they exist
                if include_person1 and hasattr(item, 'person1') and item.person1:
                    item_data['person1'] = item.person1.to_dict()
                if include_person2 and hasattr(item, 'person2') and item.person2:
                    item_data['person2'] = item.person2.to_dict()

            else:
                item_data = item.to_dict()
                if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]
                 # Include included relationship data if not using field selection
                if include_person1 and hasattr(item, 'person1') and item.person1:
                    item_data["person1"] = item.person1.to_dict()
                if include_person2 and hasattr(item, 'person2') and item.person2:
                    item_data["person2"] = item.person2.to_dict()


            # Generate links using the base URL
            item_data["_links"] = {
                "self": urljoin(base_url, f"api/relationships/{item.id}"),
                "person1": urljoin(base_url, f"api/people/{item.person1_id}"),
                "person2": urljoin(base_url, f"api/people/{item.person2_id}"),
            }

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
        abort(500, description="Database error fetching relationships.")
    except Exception as e:
        logging.error(f"Error processing relationships request: {e}", exc_info=True)
        abort(500, description="Error processing relationships request.")


def get_relationship_by_id(db: Session, relationship_id: int, fields: Optional[List[str]] = None,
                          include_person1: bool = False, include_person2: bool = False) -> Optional[Dict[str, Any]]:
    """Retrieves a single relationship by ID."""
    try:
        query = db.query(RelationshipModel).filter(RelationshipModel.id == relationship_id)

        load_options = []
        if include_person1:
            load_options.append(joinedload(RelationshipModel.person1))
        if include_person2:
            load_options.append(joinedload(RelationshipModel.person2))
        if load_options:
             query = query.options(*load_options)

        final_fields = None
        if fields:
             required_fields = {'id', 'person1_id', 'person2_id'}
             final_fields = list(set(fields) | required_fields)
             try:
                 # Apply load_only only to the RelationshipModel's columns
                 rel_model_fields = [f for f in final_fields if hasattr(RelationshipModel, f)]
                 if rel_model_fields:
                    query = query.options(load_only(*rel_model_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for Relationship ID {relationship_id}: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None


        rel_obj = query.first()

        if rel_obj is None:
            abort(404, description="Relationship not found.") # Use abort for 404

        if final_fields:
            # Manually construct dict if fields were selected, getting data from loaded objects
            item_data = {field: getattr(rel_obj, field, None) for field in final_fields if hasattr(rel_obj, field)}
            # Include included relationship fields if they exist
            if include_person1 and hasattr(rel_obj, 'person1') and rel_obj.person1:
                item_data['person1'] = rel_obj.person1.to_dict()
            if include_person2 and hasattr(rel_obj, 'person2') and rel_obj.person2:
                item_data['person2'] = rel_obj.person2.to_dict()
        else:
            item_data = rel_obj.to_dict()
            if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]
            # Include included relationship data if not using field selection
            if include_person1 and hasattr(rel_obj, 'person1') and rel_obj.person1:
                item_data["person1"] = rel_obj.person1.to_dict()
            if include_person2 and hasattr(rel_obj, 'person2') and rel_obj.person2:
                item_data["person2"] = rel_obj.person2.to_dict()

        # Use Flask's request.url_root if available
        base_url = request.url_root if request else ""
        item_data["_links"] = {
                "self": urljoin(base_url, f"api/relationships/{rel_obj.id}"),
                "person1": urljoin(base_url, f"api/people/{rel_obj.person1_id}"),
                "person2": urljoin(base_url, f"api/people/{rel_obj.person2_id}"),
            }

        return item_data # Return dict

    except SQLAlchemyError as e:
        logging.error(f"Database error fetching relationship ID {relationship_id}: {e}", exc_info=True)
        abort(500, description="Database error fetching relationship.")
    except Exception as e:
        logging.error(f"Error processing get relationship request for ID {relationship_id}: {e}", exc_info=True)
        abort(500, description="Error processing relationship request.")


def create_relationship(db: Session, relationship_data: dict) -> Dict[str, Any]:
    """Creates a new relationship."""
    try:
        new_relationship = RelationshipModel(**relationship_data)
        db.add(new_relationship)
        db.commit()
        db.refresh(new_relationship)
        return new_relationship.to_dict() # Return dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating relationship: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Relationship creation conflict (e.g., invalid person IDs).")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e):
             abort(400, description=f"Missing required field for relationship: {e}")
        abort(500, description="Database error creating relationship.")
    except Exception as e:
        logging.error(f"Error processing create relationship request: {e}", exc_info=True)
        abort(500, description="Error processing relationship creation request.")


def update_relationship(db: Session, relationship_id: int, relationship_data: dict) -> Optional[Dict[str, Any]]:
    """Updates an existing relationship."""
    try:
        relationship_obj = db.query(RelationshipModel).filter(RelationshipModel.id == relationship_id).first()
        if relationship_obj is None:
            abort(404, description="Relationship not found.")

        # Update attributes from the provided data
        for key, value in relationship_data.items():
            if hasattr(relationship_obj, key):
                setattr(relationship_obj, key, value)

        db.commit()
        db.refresh(relationship_obj)
        return relationship_obj.to_dict() # Return updated dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error updating relationship {relationship_id}: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Relationship update conflict.")
        abort(500, description="Database error updating relationship.")
    except Exception as e:
        logging.error(f"Error processing update relationship request for ID {relationship_id}: {e}", exc_info=True)
        abort(500, description="Error processing relationship update request.")


def delete_relationship(db: Session, relationship_id: int) -> bool:
    """Deletes a relationship."""
    try:
        relationship_obj = db.query(RelationshipModel).filter(RelationshipModel.id == relationship_id).first()
        if relationship_obj is None:
            abort(404, description="Relationship not found.")

        db.delete(relationship_obj)
        db.commit()
        return True # Indicate successful deletion
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error deleting relationship {relationship_id}: {e}", exc_info=True)
        abort(500, description="Database error deleting relationship.")
    except Exception as e:
        logging.error(f"Error processing delete relationship request for ID {relationship_id}: {e}", exc_info=True)
        abort(500, description="Error processing relationship deletion request.")


# --- Relationship Attribute Services (get_all implemented) ---
# Added get_by_id, create, update, delete

def get_all_relationship_attributes(db: Session, page: int = 1, page_size: int = 10,
                              order_by: str = 'id', order_direction: str = 'asc',
                              key: Optional[str] = None, value: Optional[str] = None,
                              relationship_id: Optional[int] = None,
                              fields: Optional[List[str]] = None,
                              include_relationship: bool = False) -> Dict[str, Any]:
    """Retrieves relationship attributes with pagination, filtering, sorting, field selection, and optional includes."""
    try:
        query = db.query(RelationshipAttribute)

        # Filtering
        if key:
            query = query.filter(RelationshipAttribute.key.ilike(f"%{key}%"))
        if value:
            query = query.filter(RelationshipAttribute.value.ilike(f"%{value}%"))
        if relationship_id:
            query = query.filter(RelationshipAttribute.relationship_id == relationship_id)

        total_items = query.count()

        # Sorting
        valid_order_by_columns = ['id', 'key', 'value', 'relationship_id']
        sort_column_name = order_by if order_by in valid_order_by_columns else 'id'
        order_column = getattr(RelationshipAttribute, sort_column_name)
        query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))

        # Includes
        load_options = []
        if include_relationship:
            load_options.append(joinedload(RelationshipAttribute.relationship))
        if load_options:
             query = query.options(*load_options)

        # Field selection
        final_fields = None
        if fields:
             required_fields = {'id', 'relationship_id'}
             final_fields = list(set(fields) | required_fields)
             try:
                 # Apply load_only only to the RelationshipAttribute's columns
                 attr_model_fields = [f for f in final_fields if hasattr(RelationshipAttribute, f)]
                 if attr_model_fields:
                    query = query.options(load_only(*attr_model_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for RelationshipAttribute: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None


        # Pagination
        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        # Prepare response
        results_list = []
        for item in results_orm:
            if final_fields:
                 # Manually construct dict if fields were selected
                item_data = {field: getattr(item, field, None) for field in final_fields if hasattr(item, field)}
                # Include included relationship fields if they exist
                if include_relationship and hasattr(item, 'relationship') and item.relationship:
                    item_data['relationship'] = item.relationship.to_dict()
            else:
                item_data = item.to_dict()
                if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]
                 # Include included relationship data if not using field selection
                if include_relationship and hasattr(item, 'relationship') and item.relationship:
                    item_data["relationship"] = item.relationship.to_dict()


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
        logging.error(f"Database error fetching relationship attributes: {e}", exc_info=True)
        abort(500, description="Database error fetching relationship attributes.")
    except Exception as e:
        logging.error(f"Error processing relationship attributes request: {e}", exc_info=True)
        abort(500, description="Error processing relationship attributes request.")


def get_relationship_attribute(db: Session, relationship_attribute_id: int,
                         fields: Optional[List[str]] = None,
                         include_relationship: bool = False) -> Optional[Dict[str, Any]]:
    """Retrieves a single relationship attribute by ID."""
    try:
        query = db.query(RelationshipAttribute).filter(RelationshipAttribute.id == relationship_attribute_id)

        load_options = []
        if include_relationship:
            load_options.append(joinedload(RelationshipAttribute.relationship))
        if load_options:
             query = query.options(*load_options)

        final_fields = None
        if fields:
             required_fields = {'id', 'relationship_id'}
             final_fields = list(set(fields) | required_fields)
             try:
                 # Apply load_only only to the RelationshipAttribute's columns
                 attr_model_fields = [f for f in final_fields if hasattr(RelationshipAttribute, f)]
                 if attr_model_fields:
                    query = query.options(load_only(*attr_model_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for RelationshipAttribute ID {relationship_attribute_id}: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None


        attr_obj = query.first()

        if attr_obj is None:
            abort(404, description="Relationship attribute not found.")

        if final_fields:
            # Manually construct dict if fields were selected
            item_data = {field: getattr(attr_obj, field, None) for field in final_fields if hasattr(attr_obj, field)}
            # Include included relationship fields if they exist
            if include_relationship and hasattr(attr_obj, 'relationship') and attr_obj.relationship:
                item_data['relationship'] = attr_obj.relationship.to_dict()
        else:
            item_data = attr_obj.to_dict()
            if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]
             # Include included relationship data if not using field selection
            if include_relationship and hasattr(attr_obj, 'relationship') and attr_obj.relationship:
                item_data["relationship"] = attr_obj.relationship.to_dict()

        return item_data # Return dict

    except SQLAlchemyError as e:
        logging.error(f"Database error fetching relationship attribute ID {relationship_attribute_id}: {e}", exc_info=True)
        abort(500, description="Database error fetching relationship attribute.")
    except Exception as e:
        logging.error(f"Error processing get relationship attribute request for ID {relationship_attribute_id}: {e}", exc_info=True)
        abort(500, description="Error processing relationship attribute request.")


def create_relationship_attribute(db: Session, relationship_attribute_data: dict) -> Dict[str, Any]:
    """Creates a new relationship attribute."""
    try:
        new_attribute = RelationshipAttribute(**relationship_attribute_data)
        db.add(new_attribute)
        db.commit()
        db.refresh(new_attribute)
        return new_attribute.to_dict() # Return dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating relationship attribute: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Relationship attribute creation conflict (e.g., invalid relationship ID).")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e):
             abort(400, description=f"Missing required field for relationship attribute: {e}")
        abort(500, description="Database error creating relationship attribute.")
    except Exception as e:
        logging.error(f"Error processing create relationship attribute request: {e}", exc_info=True)
        abort(500, description="Error processing relationship attribute creation request.")


def update_relationship_attribute(db: Session, relationship_attribute_id: int, relationship_attribute_data: dict) -> Optional[Dict[str, Any]]:
    """Updates an existing relationship attribute."""
    try:
        attribute_obj = db.query(RelationshipAttribute).filter(RelationshipAttribute.id == relationship_attribute_id).first()
        if attribute_obj is None:
            abort(404, description="Relationship attribute not found.")

        # Update attributes from the provided data
        for key, value in relationship_attribute_data.items():
            if hasattr(attribute_obj, key):
                setattr(attribute_obj, key, value)

        db.commit()
        db.refresh(attribute_obj)
        return attribute_obj.to_dict() # Return updated dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error updating relationship attribute {relationship_attribute_id}: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Relationship attribute update conflict.")
        abort(500, description="Database error updating relationship attribute.")
    except Exception as e:
        logging.error(f"Error processing update relationship attribute request for ID {relationship_attribute_id}: {e}", exc_info=True)
        abort(500, description="Error processing relationship attribute update request.")


def delete_relationship_attribute(db: Session, relationship_attribute_id: int) -> bool:
    """Deletes a relationship attribute."""
    try:
        attribute_obj = db.query(RelationshipAttribute).filter(RelationshipAttribute.id == relationship_attribute_id).first()
        if attribute_obj is None:
            abort(404, description="Relationship attribute not found.")

        db.delete(attribute_obj)
        db.commit()
        return True # Indicate successful deletion
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error deleting relationship attribute {relationship_attribute_id}: {e}", exc_info=True)
        abort(500, description="Database error deleting relationship attribute.")
    except Exception as e:
        logging.error(f"Error processing delete relationship attribute request for ID {relationship_attribute_id}: {e}", exc_info=True)
        abort(500, description="Error processing relationship attribute deletion request.")


# --- Person Attribute Services (get_all, get_by_id implemented) ---
# Added create, update, delete

def create_person_attribute(db: Session, person_attribute_data: dict) -> Dict[str, Any]:
    """Creates a new person attribute."""
    try:
        new_attribute = PersonAttribute(**person_attribute_data)
        db.add(new_attribute)
        db.commit()
        db.refresh(new_attribute)
        return new_attribute.to_dict() # Return dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating person attribute: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Person attribute creation conflict (e.g., invalid person ID).")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e):
             abort(400, description=f"Missing required field for person attribute: {e}")
        abort(500, description="Database error creating person attribute.")
    except Exception as e:
        logging.error(f"Error processing create person attribute request: {e}", exc_info=True)
        abort(500, description="Error processing person attribute creation request.")


def update_person_attribute(db: Session, person_attribute_id: int, person_attribute_data: dict) -> Optional[Dict[str, Any]]:
    """Updates an existing person attribute."""
    try:
        attribute_obj = db.query(PersonAttribute).filter(PersonAttribute.id == person_attribute_id).first()
        if attribute_obj is None:
            abort(404, description="Person attribute not found.")

        # Update attributes from the provided data
        for key, value in person_attribute_data.items():
            if hasattr(attribute_obj, key):
                setattr(attribute_obj, key, value)

        db.commit()
        db.refresh(attribute_obj)
        return attribute_obj.to_dict() # Return updated dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error updating person attribute {person_attribute_id}: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Person attribute update conflict.")
        abort(500, description="Database error updating person attribute.")
    except Exception as e:
        logging.error(f"Error processing update person attribute request for ID {person_attribute_id}: {e}", exc_info=True)
        abort(500, description="Error processing person attribute update request.")


def delete_person_attribute(db: Session, person_attribute_id: int) -> bool:
    """Deletes a person attribute."""
    try:
        attribute_obj = db.query(PersonAttribute).filter(PersonAttribute.id == person_attribute_id).first()
        if attribute_obj is None:
            abort(404, description="Person attribute not found.")

        db.delete(attribute_obj)
        db.commit()
        return True # Indicate successful deletion
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error deleting person attribute {person_attribute_id}: {e}", exc_info=True)
        abort(500, description="Database error deleting person attribute.")
    except Exception as e:
        logging.error(f"Error processing delete person attribute request for ID {person_attribute_id}: {e}", exc_info=True)
        abort(500, description="Error processing person attribute deletion request.")


# --- Media Services ---
# Added get_all, get_by_id, create, update, delete

def get_all_media(db: Session, page: int = 1, page_size: int = 10,
                  order_by: str = 'id', order_direction: str = 'asc',
                  file_name: Optional[str] = None, file_type: Optional[str] = None,
                  description: Optional[str] = None, fields: Optional[List[str]] = None,
                  person_id: Optional[int] = None) -> Dict[str, Any]: # Added person_id filter
    """Retrieves all media with pagination and filtering."""
    try:
        query = db.query(Media)

        # Filtering
        if file_name:
            query = query.filter(Media.file_name.ilike(f"%{file_name}%"))
        if file_type:
            query = query.filter(Media.media_type == file_type) # Assuming media_type maps to file_type
        if description:
            query = query.filter(Media.description.ilike(f"%{description}%"))
        if person_id: # Added person_id filter
             query = query.filter(Media.person_id == person_id)

        total_items = query.count()

        # Sorting
        valid_order_by_columns = ['id', 'file_name', 'media_type', 'uploaded_at', 'person_id'] # Added person_id
        sort_column_name = order_by if order_by in valid_order_by_columns else 'id'
        order_column = getattr(Media, sort_column_name)
        query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))

        # Field selection
        final_fields = None
        if fields:
             required_fields = {'id', 'file_path'} # File path is probably essential
             final_fields = list(set(fields) | required_fields)
             try:
                 query = query.options(load_only(*final_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for Media: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None

        # Pagination
        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        # Prepare response
        results_list = []
        for item in results_orm:
            if final_fields:
                item_data = {field: getattr(item, field, None) for field in final_fields if hasattr(item, field)}
            else:
                item_data = item.to_dict()
                if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

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
        logging.error(f"Database error fetching media: {e}", exc_info=True)
        abort(500, description="Database error fetching media.")
    except Exception as e:
        logging.error(f"Error processing media request: {e}", exc_info=True)
        abort(500, description="Error processing media request.")


def get_media_by_id(db: Session, media_id: int, fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single media item by ID."""
    try:
        query = db.query(Media).filter(Media.id == media_id)

        final_fields = None
        if fields:
             required_fields = {'id', 'file_path'}
             final_fields = list(set(fields) | required_fields)
             try:
                 query = query.options(load_only(*final_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for Media ID {media_id}: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None

        media_obj = query.first()

        if media_obj is None:
            abort(404, description="Media not found.")

        if final_fields:
            item_data = {field: getattr(media_obj, field, None) for field in final_fields if hasattr(media_obj, field)}
        else:
            item_data = media_obj.to_dict()
            if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

        return item_data # Return dict

    except SQLAlchemyError as e:
        logging.error(f"Database error fetching media ID {media_id}: {e}", exc_info=True)
        abort(500, description="Database error fetching media.")
    except Exception as e:
        logging.error(f"Error processing get media request for ID {media_id}: {e}", exc_info=True)
        abort(500, description="Error processing media request.")


def create_media(db: Session, media_data: dict) -> Dict[str, Any]:
    """Creates a new media item."""
    try:
        new_media = Media(**media_data)
        db.add(new_media)
        db.commit()
        db.refresh(new_media)
        return new_media.to_dict() # Return dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating media: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Media creation conflict (e.g., invalid person ID).")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e):
             abort(400, description=f"Missing required field for media: {e}")
        abort(500, description="Database error creating media.")
    except Exception as e:
        logging.error(f"Error processing create media request: {e}", exc_info=True)
        abort(500, description="Error processing media creation request.")


def update_media(db: Session, media_id: int, media_data: dict) -> Optional[Dict[str, Any]]:
    """Updates an existing media item."""
    try:
        media_obj = db.query(Media).filter(Media.id == media_id).first()
        if media_obj is None:
            abort(404, description="Media not found.")

        # Update attributes from the provided data
        for key, value in media_data.items():
            if hasattr(media_obj, key):
                setattr(media_obj, key, value)

        db.commit()
        db.refresh(media_obj)
        return media_obj.to_dict() # Return updated dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error updating media {media_id}: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Media update conflict.")
        abort(500, description="Database error updating media.")
    except Exception as e:
        logging.error(f"Error processing update media request for ID {media_id}: {e}", exc_info=True)
        abort(500, description="Error processing media update request.")


def delete_media(db: Session, media_id: int) -> bool:
    """Deletes a media item."""
    try:
        media_obj = db.query(Media).filter(Media.id == media_id).first()
        if media_obj is None:
            abort(404, description="Media not found.")

        db.delete(media_obj)
        db.commit()
        return True # Indicate successful deletion
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error deleting media {media_id}: {e}", exc_info=True)
        abort(500, description="Database error deleting media.")
    except Exception as e:
        logging.error(f"Error processing delete media request for ID {media_id}: {e}", exc_info=True)
        abort(500, description="Error processing media deletion request.")


# --- Event Services ---
# Added get_all, get_by_id, create, update, delete

def get_all_events(db: Session, page: int = 1, page_size: int = 10,
                   order_by: str = 'id', order_direction: str = 'asc',
                   type: Optional[str] = None, place: Optional[str] = None,
                   description: Optional[str] = None, fields: Optional[List[str]] = None,
                   person_id: Optional[int] = None) -> Dict[str, Any]: # Added person_id filter
    """Retrieves all events with pagination and filtering."""
    try:
        query = db.query(Event)

        # Filtering
        if type:
            query = query.filter(Event.event_type == type)
        if place:
            query = query.filter(Event.place.ilike(f"%{place}%"))
        if description:
            query = query.filter(Event.description.ilike(f"%{description}%"))
        if person_id: # Added person_id filter
            query = query.filter(Event.person_id == person_id)


        total_items = query.count()

        # Sorting
        valid_order_by_columns = ['id', 'event_type', 'date', 'place', 'person_id'] # Added person_id
        sort_column_name = order_by if order_by in valid_order_by_columns else 'id'
        order_column = getattr(Event, sort_column_name)
        query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))

        # Field selection
        final_fields = None
        if fields:
             required_fields = {'id', 'person_id'}
             final_fields = list(set(fields) | required_fields)
             try:
                 query = query.options(load_only(*final_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for Event: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None


        # Pagination
        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        # Prepare response
        results_list = []
        for item in results_orm:
            if final_fields:
                 item_data = {field: getattr(item, field, None) for field in final_fields if hasattr(item, field)}
            else:
                item_data = item.to_dict()
                if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

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
        logging.error(f"Database error fetching events: {e}", exc_info=True)
        abort(500, description="Database error fetching events.")
    except Exception as e:
        logging.error(f"Error processing events request: {e}", exc_info=True)
        abort(500, description="Error processing events request.")


def get_event_by_id(db: Session, event_id: int, fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single event by ID."""
    try:
        query = db.query(Event).filter(Event.id == event_id)

        final_fields = None
        if fields:
             required_fields = {'id', 'person_id'}
             final_fields = list(set(fields) | required_fields)
             try:
                 query = query.options(load_only(*final_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for Event ID {event_id}: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None


        event_obj = query.first()

        if event_obj is None:
            abort(404, description="Event not found.")

        if final_fields:
            item_data = {field: getattr(event_obj, field, None) for field in final_fields if hasattr(event_obj, field)}
        else:
            item_data = event_obj.to_dict()
            if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

        return item_data # Return dict

    except SQLAlchemyError as e:
        logging.error(f"Database error fetching event ID {event_id}: {e}", exc_info=True)
        abort(500, description="Database error fetching event.")
    except Exception as e:
        logging.error(f"Error processing get event request for ID {event_id}: {e}", exc_info=True)
        abort(500, description="Error processing event request.")


def create_event(db: Session, event_data: dict) -> Dict[str, Any]:
    """Creates a new event."""
    try:
        new_event = Event(**event_data)
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        return new_event.to_dict() # Return dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating event: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Event creation conflict (e.g., invalid person ID).")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e):
             abort(400, description=f"Missing required field for event: {e}")
        abort(500, description="Database error creating event.")
    except Exception as e:
        logging.error(f"Error processing create event request: {e}", exc_info=True)
        abort(500, description="Error processing event creation request.")


def update_event(db: Session, event_id: int, event_data: dict) -> Optional[Dict[str, Any]]:
    """Updates an existing event."""
    try:
        event_obj = db.query(Event).filter(Event.id == event_id).first()
        if event_obj is None:
            abort(404, description="Event not found.")

        # Update attributes from the provided data
        for key, value in event_data.items():
            if hasattr(event_obj, key):
                setattr(event_obj, key, value)

        db.commit()
        db.refresh(event_obj)
        return event_obj.to_dict() # Return updated dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error updating event {event_id}: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Event update conflict.")
        abort(500, description="Database error updating event.")
    except Exception as e:
        logging.error(f"Error processing update event request for ID {event_id}: {e}", exc_info=True)
        abort(500, description="Error processing event update request.")


def delete_event(db: Session, event_id: int) -> bool:
    """Deletes an event."""
    try:
        event_obj = db.query(Event).filter(Event.id == event_id).first()
        if event_obj is None:
            abort(404, description="Event not found.")

        db.delete(event_obj)
        db.commit()
        return True # Indicate successful deletion
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error deleting event {event_id}: {e}", exc_info=True)
        abort(500, description="Database error deleting event.")
    except Exception as e:
        logging.error(f"Error processing delete event request for ID {event_id}: {e}", exc_info=True)
        abort(500, description="Error processing event deletion request.")


# --- Source Services ---
# Added get_all, get_by_id, create, update, delete

def get_all_sources(db: Session, page: int = 1, page_size: int = 10,
                    order_by: str = 'id', order_direction: str = 'asc',
                    title: Optional[str] = None, author: Optional[str] = None,
                    fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """Retrieves all sources with pagination and filtering."""
    try:
        query = db.query(Source)

        # Filtering
        if title:
            query = query.filter(Source.title.ilike(f"%{title}%"))
        if author:
            query = query.filter(Source.author.ilike(f"%{author}%"))

        total_items = query.count()

        # Sorting
        valid_order_by_columns = ['id', 'title', 'author', 'created_at']
        sort_column_name = order_by if order_by in valid_order_by_columns else 'id'
        order_column = getattr(Source, sort_column_name)
        query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))

        # Field selection
        final_fields = None
        if fields:
             required_fields = {'id', 'title'} # Title is likely essential
             final_fields = list(set(fields) | required_fields)
             try:
                 query = query.options(load_only(*final_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for Source: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None


        # Pagination
        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        # Prepare response
        results_list = []
        for item in results_orm:
            if final_fields:
                 item_data = {field: getattr(item, field, None) for field in final_fields if hasattr(item, field)}
            else:
                item_data = item.to_dict()
                if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

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
        logging.error(f"Database error fetching sources: {e}", exc_info=True)
        abort(500, description="Database error fetching sources.")
    except Exception as e:
        logging.error(f"Error processing sources request: {e}", exc_info=True)
        abort(500, description="Error processing sources request.")


def get_source_by_id(db: Session, source_id: int, fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single source by ID."""
    try:
        query = db.query(Source).filter(Source.id == source_id)

        final_fields = None
        if fields:
             required_fields = {'id', 'title'}
             final_fields = list(set(fields) | required_fields)
             try:
                 query = query.options(load_only(*final_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for Source ID {source_id}: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None


        source_obj = query.first()

        if source_obj is None:
            abort(404, description="Source not found.")

        if final_fields:
            item_data = {field: getattr(source_obj, field, None) for field in final_fields if hasattr(source_obj, field)}
        else:
            item_data = source_obj.to_dict()
            if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

        return item_data # Return dict

    except SQLAlchemyError as e:
        logging.error(f"Database error fetching source ID {source_id}: {e}", exc_info=True)
        abort(500, description="Database error fetching source.")
    except Exception as e:
        logging.error(f"Error processing get source request for ID {source_id}: {e}", exc_info=True)
        abort(500, description="Error processing source request.")


def create_source(db: Session, source_data: dict) -> Dict[str, Any]:
    """Creates a new source."""
    try:
        new_source = Source(**source_data)
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        return new_source.to_dict() # Return dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating source: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Source creation conflict.")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e):
             abort(400, description=f"Missing required field for source: {e}")
        abort(500, description="Database error creating source.")
    except Exception as e:
        logging.error(f"Error processing create source request: {e}", exc_info=True)
        abort(500, description="Error processing source creation request.")


def update_source(db: Session, source_id: int, source_data: dict) -> Optional[Dict[str, Any]]:
    """Updates an existing source."""
    try:
        source_obj = db.query(Source).filter(Source.id == source_id).first()
        if source_obj is None:
            abort(404, description="Source not found.")

        # Update attributes from the provided data
        for key, value in source_data.items():
            if hasattr(source_obj, key):
                setattr(source_obj, key, value)

        db.commit()
        db.refresh(source_obj)
        return source_obj.to_dict() # Return updated dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error updating source {source_id}: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Source update conflict.")
        abort(500, description="Database error updating source.")
    except Exception as e:
        logging.error(f"Error processing update source request for ID {source_id}: {e}", exc_info=True)
        abort(500, description="Error processing source update request.")


def delete_source(db: Session, source_id: int) -> bool:
    """Deletes a source."""
    try:
        source_obj = db.query(Source).filter(Source.id == source_id).first()
        if source_obj is None:
            abort(404, description="Source not found.")

        db.delete(source_obj)
        db.commit()
        return True # Indicate successful deletion
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error deleting source {source_id}: {e}", exc_info=True)
        abort(500, description="Database error deleting source.")
    except Exception as e:
        logging.error(f"Error processing delete source request for ID {source_id}: {e}", exc_info=True)
        abort(500, description="Error processing source deletion request.")


# --- Citation Services ---
# Added get_all, get_by_id, create, update, delete

def get_all_citations(db: Session, page: int = 1, page_size: int = 10,
                      order_by: str = 'id', order_direction: str = 'asc',
                      source_id: Optional[int] = None, person_id: Optional[int] = None,
                      event_id: Optional[int] = None, description: Optional[str] = None,
                      fields: Optional[List[str]] = None, include_source: bool = False,
                      include_person: bool = False, include_event: bool = False) -> Dict[str, Any]:
    """Retrieves all citations with pagination and filtering."""
    try:
        query = db.query(Citation)

        # Filtering
        if source_id:
            query = query.filter(Citation.source_id == source_id)
        if person_id:
            query = query.filter(Citation.person_id == person_id)
        if event_id:
            query = query.filter(Citation.event_id == event_id)
        if description: # Assuming description maps to citation_text
            query = query.filter(Citation.citation_text.ilike(f"%{description}%"))


        total_items = query.count()

        # Sorting
        valid_order_by_columns = ['id', 'source_id', 'person_id', 'event_id', 'created_at']
        sort_column_name = order_by if order_by in valid_order_by_columns else 'id'
        order_column = getattr(Citation, sort_column_name)
        query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))

        # Includes
        load_options = []
        if include_source:
            load_options.append(joinedload(Citation.source))
        if include_person:
            load_options.append(joinedload(Citation.person))
        if include_event:
            load_options.append(joinedload(Citation.event))
        if load_options:
             query = query.options(*load_options)

        # Field selection
        final_fields = None
        if fields:
             required_fields = {'id', 'source_id'} # Source ID is likely essential
             final_fields = list(set(fields) | required_fields)
             try:
                 # Apply load_only only to the Citation's columns
                 citation_model_fields = [f for f in final_fields if hasattr(Citation, f)]
                 if citation_model_fields:
                    query = query.options(load_only(*citation_model_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for Citation: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None


        # Pagination
        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        # Prepare response
        results_list = []
        for item in results_orm:
            if final_fields:
                 # Manually construct dict if fields were selected
                item_data = {field: getattr(item, field, None) for field in final_fields if hasattr(item, field)}
                # Include included relationship fields if they exist
                if include_source and hasattr(item, 'source') and item.source:
                    item_data['source'] = item.source.to_dict()
                if include_person and hasattr(item, 'person') and item.person:
                    item_data['person'] = item.person.to_dict()
                if include_event and hasattr(item, 'event') and item.event:
                    item_data['event'] = item.event.to_dict()
            else:
                item_data = item.to_dict()
                if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]
                 # Include included relationship data if not using field selection
                if include_source and hasattr(item, 'source') and item.source:
                    item_data["source"] = item.source.to_dict()
                if include_person and hasattr(item, 'person') and item.person:
                    item_data["person"] = item.person.to_dict()
                if include_event and hasattr(item, 'event') and item.event:
                    item_data["event"] = item.event.to_dict()


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
        logging.error(f"Database error fetching citations: {e}", exc_info=True)
        abort(500, description="Database error fetching citations.")
    except Exception as e:
        logging.error(f"Error processing citations request: {e}", exc_info=True)
        abort(500, description="Error processing citations request.")


def get_citation_by_id(db: Session, citation_id: int, fields: Optional[List[str]] = None,
                       include_source: bool = False, include_person: bool = False,
                       include_event: bool = False) -> Optional[Dict[str, Any]]:
    """Retrieves a single citation by ID."""
    try:
        query = db.query(Citation).filter(Citation.id == citation_id)

        load_options = []
        if include_source:
            load_options.append(joinedload(Citation.source))
        if include_person:
            load_options.append(joinedload(Citation.person))
        if include_event:
            load_options.append(joinedload(Citation.event))
        if load_options:
             query = query.options(*load_options)

        final_fields = None
        if fields:
             required_fields = {'id', 'source_id'}
             final_fields = list(set(fields) | required_fields)
             try:
                 # Apply load_only only to the Citation's columns
                 citation_model_fields = [f for f in final_fields if hasattr(Citation, f)]
                 if citation_model_fields:
                    query = query.options(load_only(*citation_model_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for Citation ID {citation_id}: {fields}. Error: {e}. Ignoring field selection.")
                 final_fields = None


        citation_obj = query.first()

        if citation_obj is None:
            abort(404, description="Citation not found.")

        if final_fields:
            # Manually construct dict if fields were selected
            item_data = {field: getattr(citation_obj, field, None) for field in final_fields if hasattr(citation_obj, field)}
            # Include included relationship fields if they exist
            if include_source and hasattr(citation_obj, 'source') and citation_obj.source:
                item_data['source'] = citation_obj.source.to_dict()
            if include_person and hasattr(citation_obj, 'person') and citation_obj.person:
                item_data['person'] = citation_obj.person.to_dict()
            if include_event and hasattr(citation_obj, 'event') and citation_obj.event:
                item_data['event'] = citation_obj.event.to_dict()
        else:
            item_data = citation_obj.to_dict()
            if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]
             # Include included relationship data if not using field selection
            if include_source and hasattr(citation_obj, 'source') and citation_obj.source:
                item_data["source"] = citation_obj.source.to_dict()
            if include_person and hasattr(citation_obj, 'person') and citation_obj.person:
                item_data["person"] = citation_obj.person.to_dict()
            if include_event and hasattr(citation_obj, 'event') and citation_obj.event:
                item_data["event"] = citation_obj.event.to_dict()


        return item_data # Return dict

    except SQLAlchemyError as e:
        logging.error(f"Database error fetching citation ID {citation_id}: {e}", exc_info=True)
        abort(500, description="Database error fetching citation.")
    except Exception as e:
        logging.error(f"Error processing get citation request for ID {citation_id}: {e}", exc_info=True)
        abort(500, description="Error processing citation request.")


def create_citation(db: Session, citation_data: dict) -> Dict[str, Any]:
    """Creates a new citation."""
    try:
        new_citation = Citation(**citation_data)
        db.add(new_citation)
        db.commit()
        db.refresh(new_citation)
        return new_citation.to_dict() # Return dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating citation: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Citation creation conflict (e.g., invalid foreign key).")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e):
             abort(400, description=f"Missing required field for citation: {e}")
        abort(500, description="Database error creating citation.")
    except Exception as e:
        logging.error(f"Error processing create citation request: {e}", exc_info=True)
        abort(500, description="Error processing citation creation request.")


def update_citation(db: Session, citation_id: int, citation_data: dict) -> Optional[Dict[str, Any]]:
    """Updates an existing citation."""
    try:
        citation_obj = db.query(Citation).filter(Citation.id == citation_id).first()
        if citation_obj is None:
            abort(404, description="Citation not found.")

        # Update attributes from the provided data
        for key, value in citation_data.items():
            if hasattr(citation_obj, key):
                setattr(citation_obj, key, value)

        db.commit()
        db.refresh(citation_obj)
        return citation_obj.to_dict() # Return updated dict
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error updating citation {citation_id}: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
             abort(409, description="Citation update conflict.")
        abort(500, description="Database error updating citation.")
    except Exception as e:
        logging.error(f"Error processing update citation request for ID {citation_id}: {e}", exc_info=True)
        abort(500, description="Error processing citation update request.")


def delete_citation(db: Session, citation_id: int) -> bool:
    """Deletes a citation."""
    try:
        citation_obj = db.query(Citation).filter(Citation.id == citation_id).first()
        if citation_obj is None:
            abort(404, description="Citation not found.")

        db.delete(citation_obj)
        db.commit()
        return True # Indicate successful deletion
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error deleting citation {citation_id}: {e}", exc_info=True)
        abort(500, description="Database error deleting citation.")
    except Exception as e:
        logging.error(f"Error processing delete citation request for ID {citation_id}: {e}", exc_info=True)
        abort(500, description="Error processing citation deletion request.")


# --- Tree Traversal Services (Ancestors and Descendants implemented) ---
# Added placeholder for get_partial_tree and added missing traversal functions as placeholders

def get_ancestors(db: Session, person_id: int, depth: int) -> List[Dict[str, Any]]: # Changed return type to list of dicts
    """Retrieves ancestors using an iterative approach."""
    ancestors = []
    queue = [(person_id, 0)]
    visited_ids = {person_id}

    # Check if the starting person exists
    starting_person = db.query(Person).filter(Person.id == person_id).first()
    if not starting_person:
         logging.warning(f"Starting person ID {person_id} not found for get_ancestors.")
         abort(404, description=f"Person with ID {person_id} not found.")


    while queue:
        current_id, current_depth = queue.pop(0)

        if current_depth >= depth:
            continue

        parent_rels = db.query(RelationshipModel).filter(
            RelationshipModel.person2_id == current_id,
            RelationshipModel.rel_type == 'parent' # Assuming 'parent' relationship type
        ).options(joinedload(RelationshipModel.person1)).all() # Eager load person1 (the parent)

        for rel in parent_rels:
            parent = rel.person1
            if parent and parent.id not in visited_ids:
                ancestors.append(parent.to_dict()) # Append dict
                visited_ids.add(parent.id)
                queue.append((parent.id, current_depth + 1))
    return ancestors # Return list of dicts

def get_descendants(db: Session, person_id: int, depth: int) -> List[Dict[str, Any]]: # Changed return type to list of dicts
    """Retrieves descendants using an iterative approach."""
    descendants = []
    queue = [(person_id, 0)]
    visited_ids = {person_id}

    # Check if the starting person exists
    starting_person = db.query(Person).filter(Person.id == person_id).first()
    if not starting_person:
         logging.warning(f"Starting person ID {person_id} not found for get_descendants.")
         abort(404, description=f"Person with ID {person_id} not found.")

    while queue:
        current_id, current_depth = queue.pop(0)

        if current_depth >= depth:
            continue

        child_rels = db.query(RelationshipModel).filter(
            RelationshipModel.person1_id == current_id,
            RelationshipModel.rel_type == 'parent' # Assuming 'parent' relationship type implies person2 is the child
        ).options(joinedload(RelationshipModel.person2)).all() # Eager load person2 (the child)

        for rel in child_rels:
            child = rel.person2
            if child and child.id not in visited_ids:
                descendants.append(child.to_dict()) # Append dict
                visited_ids.add(child.id)
                queue.append((child.id, current_depth + 1))
    return descendants # Return list of dicts

def get_partial_tree(db: Session, person_id: int, depth: int, only_ancestors: bool, only_descendants: bool) -> Dict[str, Any]:
    """Retrieves a partial tree (ancestors and/or descendants) for a person (Placeholder)."""
    logging.warning(f"Tree traversal service 'get_partial_tree' for ID {person_id} is a placeholder.")
    # TODO: Implement actual logic to fetch partial tree data
    # Example placeholder return structure:
    center_person = get_person_by_id_db(db, person_id) # Use existing service to get center person

    ancestors_list = []
    descendants_list = []

    if not only_descendants: # If not only descendants, get ancestors
        # Implement logic to get ancestors up to depth
        pass # Placeholder for ancestor fetching logic

    if not only_ancestors: # If not only ancestors, get descendants
        # Implement logic to get descendants up to depth
        pass # Placeholder for descendant fetching logic


    return {
        "center": center_person, # The central person (as a dict)
        "ancestors": ancestors_list, # List of ancestor Person objects (as dicts)
        "descendants": descendants_list # List of descendant Person objects (as dicts)
    }

# ADDED: Placeholder functions for missing tree traversal services
def get_extended_family(db: Session, person_id: int, depth: int) -> List[Dict[str, Any]]:
    """Retrieves extended family (siblings, cousins, etc.) (Placeholder)."""
    logging.warning(f"Tree traversal service 'get_extended_family' for ID {person_id} is a placeholder.")
    # TODO: Implement actual logic to fetch extended family
    return [] # Return empty list for now

def get_related(db: Session, person_id: int, depth: int) -> List[Dict[str, Any]]:
    """Retrieves related people (in-laws, step-relations, etc.) (Placeholder)."""
    logging.warning(f"Tree traversal service 'get_related' for ID {person_id} is a placeholder.")
    # TODO: Implement actual logic to fetch related people
    return [] # Return empty list for now

# --- Search Service (Implemented) ---
# This function seems to have basic implementation already.

def search_people(db: Session, name: Optional[str] = None, birth_date: Optional[date] = None,
                  death_date: Optional[date] = None, gender: Optional[str] = None,
                  place_of_birth: Optional[str] = None, place_of_death: Optional[str] = None,
                  notes: Optional[str] = None, attribute_key: Optional[str] = None,
                  attribute_value: Optional[str] = None) -> List[Dict[str, Any]]: # Changed return type
    """Searches people based on multiple criteria."""
    try:
        query = db.query(Person)

        if name:
            name_filter = f"%{name}%"
            query = query.filter(or_(
                Person.first_name.ilike(name_filter),
                Person.last_name.ilike(name_filter),
                Person.nickname.ilike(name_filter)
            ))
        if birth_date:
            query = query.filter(Person.birth_date == birth_date)
        if death_date:
            query = query.filter(Person.death_date == death_date)
        if gender:
            query = query.filter(Person.gender == gender)
        if place_of_birth:
            query = query.filter(Person.place_of_birth.ilike(f"%{place_of_birth}%"))
        if place_of_death:
            query = query.filter(Person.place_of_death.ilike(f"%{place_of_death}%"))
        if notes:
            query = query.filter(Person.notes.ilike(f"%{notes}%"))

        if attribute_key or attribute_value:
            # Assuming Person model has relationship named 'attributes' to PersonAttribute
            query = query.join(Person.attributes)
            if attribute_key:
                query = query.filter(PersonAttribute.key == attribute_key)
            if attribute_value:
                query = query.filter(PersonAttribute.value.ilike(f"%{attribute_value}%"))
            query = query.distinct()

        results = query.all()
        return [p.to_dict() for p in results] # Return list of dicts
    except SQLAlchemyError as e:
        logging.error(f"Database error during person search: {e}", exc_info=True)
        abort(500, description="Database error during search.")


def get_person_relationships_and_attributes(db: Session, person_id: int) -> Dict[str, Any]:
    """Retrieves relationships and attributes for a specific person."""
    try:
        person_obj = db.query(Person).filter(Person.id == person_id).first()
        if not person_obj:
            abort(404, description="Person not found")

        person_attrs = db.query(PersonAttribute)\
                         .filter(PersonAttribute.person_id == person_id)\
                         .all()

        person_rels_orm = db.query(RelationshipModel)\
                            .filter(or_(RelationshipModel.person1_id == person_id,
                                        RelationshipModel.person2_id == person_id))\
                            .options(joinedload(RelationshipModel.attributes),
                                     joinedload(RelationshipModel.person1),
                                     joinedload(RelationshipModel.person2))\
                            .all()

        person_attributes_data = [attr.to_dict() for attr in person_attrs] # Assuming to_dict exists
        relationships_data = []
        for rel in person_rels_orm:
            rel_data = rel.to_dict() # Assuming to_dict exists
            if "_sa_instance_state" in rel_data: del rel_data["_sa_instance_state"]

            rel_data['attributes'] = [rel_attr.to_dict() for rel_attr in rel.attributes] # Assuming to_dict exists
            for attr_dict in rel_data['attributes']:
                 if "_sa_instance_state" in attr_dict: del attr_dict["_sa_instance_state"]

            if rel.person1:
                p1_data = rel.person1.to_dict() # Assuming to_dict exists
                if "_sa_instance_state" in p1_data: del p1_data["_sa_instance_state"]
                rel_data['person1'] = p1_data
            else:
                 rel_data['person1'] = None

            if rel.person2:
                p2_data = rel.person2.to_dict() # Assuming to_dict exists
                if "_sa_instance_state" in p2_data: del p2_data["_sa_instance_state"]
                rel_data['person2'] = p2_data
            else:
                 rel_data['person2'] = None

            relationships_data.append(rel_data)

        return {
            "person_attributes": person_attributes_data,
            "relationships": relationships_data
        }
    except NoResultFound:
        abort(404, description="Person not found")
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching relationships/attributes for person {person_id}: {e}", exc_info=True)
        abort(500, description="Database error fetching relationships/attributes.")

# Ensure no trailing code or incorrect indentation below this line
