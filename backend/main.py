# backend/main.py
import logging
from urllib.parse import urljoin
from sqlalchemy.orm import Session, load_only, joinedload
from sqlalchemy.exc import SQLAlchemyError, NoResultFound, IntegrityError
from sqlalchemy import or_, and_, desc, asc
from typing import Optional, List, Dict, Any
from datetime import date
from flask import abort, request

# --- User Services ---

def get_all_users(db: Session) -> List[User]:
    try:
        return db.query(User).all()
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching all users: {e}", exc_info=True)
        abort(500, description="Database error fetching users.")

def get_user_by_id(db: Session, user_id: int) -> User:
    try:
        user_obj = db.query(User).filter(User.id == user_id).first()
        if user_obj is None:
            abort(404, description="User not found")
        return user_obj
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching user ID {user_id}: {e}", exc_info=True)
        abort(500, description="Database error fetching user.")

def create_user(db: Session, user_data: dict) -> User:
    try:
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

# --- Person Services ---

def get_all_people_db(db: Session, page: int = 1, page_size: int = 10, order_by: str = 'id',
                      order_direction: str = 'asc', name: Optional[str] = None,
                      gender: Optional[str] = None, birth_date: Optional[date] = None,
                      death_date: Optional[date] = None, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    try:
        query = db.query(Person)
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

        valid_order_by_columns = ['id', 'first_name', 'last_name', 'gender', 'birth_date', 'death_date']
        sort_column_name = order_by if order_by in valid_order_by_columns else 'id'
        order_column = getattr(Person, sort_column_name)
        query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))

        final_fields = None
        if fields:
            try:
                required_fields = {'id'}
                final_fields = list(set(fields) | required_fields)
                query = query.options(load_only(*final_fields))
            except Exception as e:
                logging.warning(f"Invalid fields requested for Person: {fields}. Error: {e}. Ignoring.")
                final_fields = None

        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

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
        abort(500, description="Database error fetching people.")
    except Exception as e:
        logging.error(f"Error processing people request: {e}", exc_info=True)
        abort(500, description="Error processing people request.")

def get_all_people_with_media_db(db: Session, page: int = 1, page_size: int = 10,
                                order_by: str = 'id', order_direction: str = 'asc',
                                name: Optional[str] = None, gender: Optional[str] = None,
                                birth_date: Optional[date] = None, death_date: Optional[date] = None,
                                fields: Optional[List[str]] = None) -> Dict[str, Any]:
    try:
        query = db.query(Person).options(joinedload(Person.media))
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

        valid_order_by_columns = ['id', 'first_name', 'last_name', 'gender', 'birth_date', 'death_date']
        sort_column_name = order_by if order_by in valid_order_by_columns else 'id'
        order_column = getattr(Person, sort_column_name)
        query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))

        final_fields = None
        if fields:
            try:
                required_fields = {'id'}
                final_fields = list(set(fields) | required_fields)
                query = query.options(load_only(*final_fields))
            except Exception as e:
                logging.warning(f"Invalid fields requested for Person with Media: {fields}. Error: {e}. Ignoring.")
                final_fields = None

        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        results_list = []
        for item in results_orm:
            if final_fields:
                item_data = {field: getattr(item, field, None) for field in final_fields}
            else:
                item_data = item.to_dict()
            item_data['media'] = [media.to_dict() for media in item.media]
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
        logging.error(f"Database error fetching people with media: {e}", exc_info=True)
        abort(500, description="Database error fetching people with media.")

def get_person_by_id_db(db: Session, person_id: int, fields: Optional[List[str]] = None) -> Dict[str, Any]:
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
    except NoResultFound:
        abort(404, description="Person not found")
    except SQLAlchemyError as e:
        logging.error(f"Database error fetching person ID {person_id}: {e}", exc_info=True)
        abort(500, description="Database error fetching person.")
    except Exception as e:
        logging.error(f"Error processing get person request for ID {person_id}: {e}", exc_info=True)
        abort(500, description="Error processing person request.")

def create_person_db(db: Session, person_data: dict) -> Dict[str, Any]:
    try:
        new_person = Person(**person_data)
        db.add(new_person)
        db.commit()
        db.refresh(new_person)
        return new_person.to_dict()
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error creating person: {e}", exc_info=True)
        if isinstance(e, IntegrityError):
            abort(409, description="Person creation conflict.")
        elif "NOT NULL constraint failed" in str(e) or "null value in column" in str(e):
            abort(400, description=f"Missing required field for person: {e}")
        abort(500, description="Database error creating person.")

def update_person_db(db: Session, person_id: int, person_data: dict) -> Optional[Dict[str, Any]]:
    try:
        person_obj = db.query(Person).filter(Person.id == person_id).first()
        if person_obj is None:
            abort(404, description="Person not found")
        for key, value in person_data.items():
            if hasattr(person_obj, key):
                setattr(person_obj, key, value)
        db.commit()
        db.refresh(person_obj)
        return person_obj.to_dict()
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
    try:
        person_obj = db.query(Person).filter(Person.id == person_id).first()
        if person_obj is None:
            abort(404, description="Person not found")
        db.delete(person_obj)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error deleting person {person_id}: {e}", exc_info=True)
        abort(500, description="Database error deleting person.")
    except Exception as e:
        logging.error(f"Error processing delete person request for ID {person_id}: {e}", exc_info=True)
        abort(500, description="Error processing person deletion request.")

# --- Relationship Services ---

def get_all_relationships(db: Session, page: int = 1, page_size: int = 10,
                          order_by: str = 'id', order_direction: str = 'asc',
                          type: Optional[str] = None, person1_id: Optional[int] = None,
                          person2_id: Optional[int] = None, fields: Optional[List[str]] = None,
                          include_person1: bool = False, include_person2: bool = False) -> Dict[str, Any]:
    try:
        query = db.query(RelationshipModel)
        if type:
            query = query.filter(RelationshipModel.rel_type == type)
        if person1_id:
            query = query.filter(RelationshipModel.person1_id == person1_id)
        if person2_id:
            query = query.filter(RelationshipModel.person2_id == person2_id)

        total_items = query.count()

        valid_order_by_columns = ['id', 'rel_type', 'person1_id', 'person2_id']
        sort_column_name = order_by if order_by in valid_order_by_columns else 'id'
        order_column = getattr(RelationshipModel, sort_column_name)
        query = query.order_by(desc(order_column) if order_direction == 'desc' else asc(order_column))

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
                query = query.options(load_only(*final_fields))
            except Exception as e:
                logging.warning(f"Invalid fields requested for Relationship: {fields}. Error: {e}. Ignoring.")
                final_fields = None

        offset = (page - 1) * page_size
        results_orm = query.offset(offset).limit(page_size).all()

        results_list = []
        for item in results_orm:
            if final_fields:
                item_data = {field: getattr(item, field, None) for field in final_fields}
            else:
                item_data = item.to_dict()
            if include_person1 and hasattr(item, 'person1'):
                item_data['person1'] = item.person1.to_dict() if item.person1 else None
            if include_person2 and hasattr(item, 'person2'):
                item_data['person2'] = item.person2.to_dict() if item.person2 else None
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
        logging.error(f"Database error fetching relationships: {e}", exc_info=True)
        abort(500, description="Database error fetching relationships.")
    except Exception as e:
        logging.error(f"Error processing relationships request: {e}", exc_info=True)
        abort(500, description="Error processing relationships request.")
