# backend/app/services.py
import logging
from urllib.parse import urljoin
from sqlalchemy.orm import Session, load_only, joinedload
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy import or_, and_, desc, asc
from typing import Optional, List, Dict, Any
from datetime import date
from fastapi import Request, HTTPException

# Import models using relative paths
try:
    from app.models.user import User
    from app.models.person import Person
    from app.models.person_attribute import PersonAttribute
    from app.models.relationship import Relationship as RelationshipModel
    from app.models.relationship_attribute import RelationshipAttribute
    from app.models.media import Media
    from app.models.event import Event
    from app.models.source import Source
    from app.models.citation import Citation
except ImportError as e:
    logging.critical(f"Failed to import models in services: {e}")
    raise

# --- User Services ---

def get_all_users(db: Session) -> List[User]:
    """Retrieves all users from the database."""
    try:
        return db.query(User).all()
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching all users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching users.")

def get_user_by_id(db: Session, user_id: int) -> User:
    """Retrieves a single user by their ID."""
    try:
        user_obj = db.query(User).filter(User.id == user_id).first()
        if user_obj is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user_obj
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching user ID {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching user.")

def create_user(db: Session, user_data: dict) -> User:
    """Creates a new user."""
    try:
        # Password hashing should be handled elsewhere
        new_user = User(**user_data)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating user: {e}", exc_info=True)
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
                 item_data = item.to_dict()
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
        raise HTTPException(status_code=500, detail="Database error fetching people.")
    except Exception as e:
        logging.error(f"Error processing people request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing people request.")


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
            raise HTTPException(status_code=404, detail="Person not found")

        if final_fields:
            response_data = {field: getattr(person_obj, field, None) for field in final_fields}
        else:
            response_data = person_obj.to_dict()
            if "_sa_instance_state" in response_data:
                 del response_data["_sa_instance_state"]

        return response_data

    except NoResultFound:
         raise HTTPException(status_code=404, detail="Person not found")
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching person ID {person_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching person.")
    except Exception as e:
        logging.error(f"Error processing get person request for ID {person_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing person request.")

def create_person_db(db: Session, person_data: dict) -> Person:
    """Creates a new person in the database."""
    try:
        new_person = Person(**person_data)
        db.add(new_person)
        db.commit()
        db.refresh(new_person)
        return new_person
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating person: {e}", exc_info=True)
        if "UNIQUE constraint failed" in str(e) or "duplicate key value violates unique constraint" in str(e):
             raise HTTPException(status_code=409, detail="Person creation conflict.")
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
                query = query.options(load_only(*final_fields))
            except Exception as e:
                 logging.warning(f"Invalid fields requested for Relationship: {fields}. Error: {e}. Ignoring.")
                 final_fields = None

        # Pagination
        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        # Prepare response data
        results_list = []
        base_url = str(request.base_url)
        for item in results_orm:
            if final_fields:
                item_data = {field: getattr(item, field, None) for field in final_fields}
            else:
                item_data = item.to_dict()
                if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

            item_data["_links"] = {
                "self": urljoin(base_url, f"/api/relationships/{item.id}"),
                "person1": urljoin(base_url, f"/api/people/{item.person1_id}"),
                "person2": urljoin(base_url, f"/api/people/{item.person2_id}"),
            }

            if include_person1 and hasattr(item, 'person1') and item.person1:
                item_data["person1"] = item.person1.to_dict()
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

# --- Relationship Attribute Services ---
# --- Implement similarly ---

# --- Person Attribute Services ---

def get_all_person_attributes(db: Session, page: int = 1, page_size: int = 10,
                              order_by: str = 'id', order_direction: str = 'asc',
                              key: Optional[str] = None, value: Optional[str] = None,
                              person_id: Optional[int] = None,
                              fields: Optional[List[str]] = None,
                              include_person: bool = False) -> Dict[str, Any]:
    """Retrieves person attributes with pagination, filtering, sorting, field selection, and optional includes."""
    try:
        query = db.query(PersonAttribute)

        # Filtering
        if key:
            query = query.filter(PersonAttribute.key.ilike(f"%{key}%"))
        if value:
            query = query.filter(PersonAttribute.value.ilike(f"%{value}%"))
        if person_id:
            query = query.filter(PersonAttribute.person_id == person_id)

        total_items = query.count()

        # Sorting
        valid_order_by_columns = ['id', 'key', 'value', 'person_id']
        sort_column_name = order_by if order_by in valid_order_by_columns else 'id'
        order_column = getattr(PersonAttribute, sort_column_name)
        query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))

        # Includes
        load_options = []
        if include_person:
            load_options.append(joinedload(PersonAttribute.person))
        if load_options:
             query = query.options(*load_options)

        # Field selection
        final_fields = None
        if fields:
             required_fields = {'id', 'person_id'}
             final_fields = list(set(fields) | required_fields)
             try:
                 query = query.options(load_only(*final_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for PersonAttribute: {fields}. Error: {e}. Ignoring.")
                 final_fields = None

        # Pagination
        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        # Prepare response
        results_list = []
        for item in results_orm:
            if final_fields:
                item_data = {field: getattr(item, field, None) for field in final_fields}
            else:
                item_data = item.to_dict()
                if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

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
        query = db.query(PersonAttribute).filter(PersonAttribute.id == person_attribute_id)

        load_options = []
        if include_person:
            load_options.append(joinedload(PersonAttribute.person))
        if load_options:
             query = query.options(*load_options)

        final_fields = None
        if fields:
             required_fields = {'id', 'person_id'}
             final_fields = list(set(fields) | required_fields)
             try:
                 query = query.options(load_only(*final_fields))
             except Exception as e:
                 logging.warning(f"Invalid fields requested for PersonAttribute ID {person_attribute_id}: {fields}. Error: {e}. Ignoring.")
                 final_fields = None

        attr_obj = query.first()

        if attr_obj is None:
            return None

        if final_fields:
            item_data = {field: getattr(attr_obj, field, None) for field in final_fields}
        else:
            item_data = attr_obj.to_dict()
            if "_sa_instance_state" in item_data: del item_data["_sa_instance_state"]

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
# --- Implement similarly ---

# --- Tree Traversal Services ---

def get_ancestors(db: Session, person_id: int, depth: int) -> List[Person]:
    """Retrieves ancestors using an iterative approach."""
    ancestors = []
    queue = [(person_id, 0)]
    visited_ids = {person_id}

    while queue:
        current_id, current_depth = queue.pop(0)

        if current_depth >= depth:
            continue

        parent_rels = db.query(RelationshipModel).filter(
            RelationshipModel.person2_id == current_id,
            RelationshipModel.rel_type == 'parent'
        ).options(joinedload(RelationshipModel.person1)).all()

        for rel in parent_rels:
            parent = rel.person1
            if parent and parent.id not in visited_ids:
                ancestors.append(parent)
                visited_ids.add(parent.id)
                queue.append((parent.id, current_depth + 1))
    return ancestors

def get_descendants(db: Session, person_id: int, depth: int) -> List[Person]:
    """Retrieves descendants using an iterative approach."""
    descendants = []
    queue = [(person_id, 0)]
    visited_ids = {person_id}

    while queue:
        current_id, current_depth = queue.pop(0)

        if current_depth >= depth:
            continue

        child_rels = db.query(RelationshipModel).filter(
            RelationshipModel.person1_id == current_id,
            RelationshipModel.rel_type == 'parent'
        ).options(joinedload(RelationshipModel.person2)).all()

        for rel in child_rels:
            child = rel.person2
            if child and child.id not in visited_ids:
                descendants.append(child)
                visited_ids.add(child.id)
                queue.append((child.id, current_depth + 1))
    return descendants


# --- Implement get_extended_family, get_related, get_partial_tree, get_branch similarly ---

# --- Search Service ---
def search_people(db: Session, name: Optional[str] = None, birth_date: Optional[date] = None,
                  death_date: Optional[date] = None, gender: Optional[str] = None,
                  place_of_birth: Optional[str] = None, place_of_death: Optional[str] = None,
                  notes: Optional[str] = None, attribute_key: Optional[str] = None,
                  attribute_value: Optional[str] = None) -> List[Person]:
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

        return query.all()
    except SQLAlchemyError as e:
        logging.error(f"Database error during person search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error during search.")


def get_person_relationships_and_attributes(db: Session, person_id: int) -> Dict[str, Any]:
    """Retrieves relationships and attributes for a specific person."""
    try:
        person_obj = db.query(Person).filter(Person.id == person_id).first()
        if not person_obj:
            raise HTTPException(status_code=404, detail="Person not found")

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

        person_attributes_data = [attr.to_dict() for attr in person_attrs]
        relationships_data = []
        for rel in person_rels_orm:
            rel_data = rel.to_dict()
            if "_sa_instance_state" in rel_data: del rel_data["_sa_instance_state"]

            rel_data['attributes'] = [rel_attr.to_dict() for rel_attr in rel.attributes]
            for attr_dict in rel_data['attributes']:
                 if "_sa_instance_state" in attr_dict: del attr_dict["_sa_instance_state"]

            if rel.person1:
                p1_data = rel.person1.to_dict()
                if "_sa_instance_state" in p1_data: del p1_data["_sa_instance_state"]
                rel_data['person1'] = p1_data
            else:
                 rel_data['person1'] = None

            if rel.person2:
                p2_data = rel.person2.to_dict()
                if "_sa_instance_state" in p2_data: del p2_data["_sa_instance_state"]
                rel_data['person2'] = p2_data
            else:
                 rel_data['person2'] = None

            relationships_data.append(rel_data)

        # Corrected indentation for the return statement
        return {
            "person_attributes": person_attributes_data,
            "relationships": relationships_data
        }
    # Correct indentation for the except blocks
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Person not found")
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching relationships/attributes for person {person_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error fetching relationships/attributes.")

# Ensure no trailing code or incorrect indentation below this line
