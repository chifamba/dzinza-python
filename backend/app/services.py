from urllib.parse import urljoin


from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, and_
from sqlalchemy.orm import load_only
from sqlalchemy import desc, asc

from sqlalchemy import Column

from typing import Optional

from datetime import date, datetime
from sqlalchemy import String
from app.models import user, person, person_attribute, relationship, relationship_attribute, media, event, source, citation, relationship
from urllib.parse import urljoin
from fastapi import Request

from fastapi import HTTPException


def get_all_users(db: Session):
    try:
        return db.query(user.User).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_user_by_id(db: Session, user_id: int):
    try:
        user_obj = db.query(user.User).filter(user.User.id == user_id).first()
        if user_obj is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user_obj
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))

def get_person_relationships_and_attributes(db: Session, person_id: int):
    """
    Retrieves all relationships and attributes associated with a given Person.
    Args:
        db: The database session.
        person_id: The ID of the person.
    Returns:
        A dictionary containing the person's attributes and relationships.
    """
    try:
        person_obj = get_person_by_id(db, person_id)
        if person_obj is None:
            raise HTTPException(status_code=404, detail="Person not found")

        person_attributes = db.query(person_attribute.PersonAttribute).filter(person_attribute.PersonAttribute.person_id == person_id).all()

        relationships = db.query(relationship.Relationship).filter(
            or_(relationship.Relationship.person1_id == person_id, relationship.Relationship.person2_id == person_id)
        ).all()
        
        relationships_data = []
        for rel in relationships:
            rel_attributes = db.query(relationship_attribute.RelationshipAttribute).filter(
            relationship_attribute.RelationshipAttribute.relationship_id == rel.id
            ).all()
            rel_data = {
                "id": rel.id,
                "type": rel.rel_type,
                "person1_id": rel.person1_id,
                "person2_id": rel.person2_id,
                "attributes": [{"id": attr.id, "key": attr.key, "value": attr.value, "relationship_id": attr.relationship_id} for attr in rel_attributes]
            }
            relationships_data.append(rel_data)

        return {
            "person_attributes": [{"id": attr.id, "key": attr.key, "value": attr.value, "person_id": attr.person_id} for attr in person_attributes],
            "relationships": relationships_data
        }
    except SQLAlchemyError as e:        
        raise HTTPException(status_code=500, detail=str(e))


def search_people(db: Session, name: str = None, birth_date: date = None, death_date: date = None,
                  gender: str = None, place_of_birth: str = None, place_of_death: str = None,
                  notes: str = None, attribute_key: str = None, attribute_value: str = None):
    """
    Searches for people based on various criteria.
    Args:
        db: The database session.
        name: Partial name to search for.
        birth_date: Birth date to match.
        death_date: Death date to match.
        gender: Gender to match.
        place_of_birth: Place of birth to match.
        place_of_death: Place of death to match.
        notes: Notes to match.
        attribute_key: key of the attribute to match
        attribute_value: value of the attribute to match
    Returns:
        A list of Person objects matching the criteria.
    """
    try:
        query = db.query(person.Person)

        if name:
            query = query.filter(person.Person.name.ilike(f"%{name}%"))
        if birth_date:
            query = query.filter(person.Person.birth_date == birth_date)
        if death_date:
            query = query.filter(person.Person.death_date == death_date)
        if gender:
            query = query.filter(person.Person.gender == gender)
        return query.all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def filter_people(db: Session, people: list, name: str = None, birth_date: date = None, death_date: date = None,
                   gender: str = None, place_of_birth: str = None, place_of_death: str = None,
                   notes: str = None, attribute_key: str = None, attribute_value: str = None):
    """
    Filters a list of people based on various criteria.
    Args:
        db: The database session.
        people: list of people to filter
        name: Partial name to search for.
        birth_date: Birth date to match.
        death_date: Death date to match.
        gender: Gender to match.
        place_of_birth: Place of birth to match.
        place_of_death: Place of death to match.
        notes: Notes to match.
        attribute_key: key of the attribute to match
        attribute_value: value of the attribute to match
    Returns:
        A list of Person objects matching the criteria.
    """
    try:
        filtered_people = people
        if name:
            filtered_people = [p for p in filtered_people if name.lower() in p.name.lower()]
        if birth_date:
            filtered_people = [p for p in filtered_people if p.birth_date == birth_date]
        if death_date:
            filtered_people = [p for p in filtered_people if p.death_date == death_date]
        if gender:
            filtered_people = [p for p in filtered_people if p.gender == gender]
        return filtered_people

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

def create_user(db: Session, user_data: dict):
    try:
        new_user = user.User(**user_data)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def get_ancestors(db: Session, person_id: int, depth: int):
    """
    Retrieves the ancestors of a person up to a certain depth.

    This function uses a Breadth-First Search (BFS) algorithm to traverse
    the family tree upwards from the given person. It starts from the person
    specified by `person_id` and traverses up the tree through 'parent'
    relationships.

    The function maintains a queue of (person_id, current_depth) pairs. It
    iteratively processes the queue, exploring each person's parents and
    adding them to the queue if the current depth is less than the specified
    `depth`.

    Args:
        db: The database session.
        person_id: The ID of the person.
        depth: The maximum depth to traverse upwards.

    Returns:
        A list of Person objects representing the ancestors.
    """
    """
    Retrieves the ancestors of a person up to a certain depth.
    Args:
        db: The database session.
        person_id: The ID of the person.
        depth: The maximum depth to traverse.
    Returns:
        A list of Person objects representing the ancestors.
    """
    try:
        if depth <= 0:
            return []

        ancestors = []
        queue = [(person_id, 0)]  # (person_id, current_depth)

        while queue:
            current_person_id, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            person_obj = get_person_by_id(db, current_person_id)
            relationships = db.query(relationship.Relationship).filter(relationship.Relationship.person2_id == current_person_id, relationship.Relationship.rel_type == 'parent').all()

            for rel in relationships:
                if rel.person1_id not in [p.id for p in ancestors]:
                    ancestors.append(get_person_by_id(db, rel.person1_id))
                queue.append((rel.person1_id, current_depth + 1))
        return ancestors

    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))

def get_branch(db: Session, person_id: int, depth: int):
    """
    Retrieves a single branch of the tree up to a given depth.

    This function uses a Breadth-First Search (BFS) algorithm to traverse the
    family tree downwards from the given person. It starts from the person
    specified by `person_id` and traverses down the tree through 'parent'
    relationships.

    The function maintains a queue of (person_id, current_depth) pairs. It
    iteratively processes the queue, exploring each person's children and
    adding them to the queue if the current depth is less than the specified
    `depth`.

    Args:
        db: The database session.
        person_id: The ID of the person at the start of the branch.
        depth: The maximum depth to traverse.
    Returns:
        A list of Person objects representing the branch.
    """
    """
    Retrieves a single branch of the tree up to a given depth.
    Args:
        db: The database session.
        person_id: The ID of the person at the start of the branch.
        depth: The maximum depth to traverse.
    Returns:
        A list of Person objects representing the branch.
    """
    try:
        if depth <= 0:
            return []

        branch = []
        queue = [(person_id, 0)]  # (person_id, current_depth)
        while queue:
            current_person_id, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            person_obj = get_person_by_id(db, current_person_id)
            branch.append(person_obj)
            relationships = db.query(relationship.Relationship).filter(relationship.Relationship.person1_id == current_person_id, relationship.Relationship.rel_type == 'parent').all()
            for rel in relationships:
                queue.append((rel.person2_id, current_depth + 1))
        return branch
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))

def get_partial_tree(db: Session, person_id: int, depth: int, only_ancestors: bool = False, only_descendants: bool = False):
    """
    Loads a partial tree around the specified person_id, up to the given depth,
    and optionally specifying if only ancestors or descendants should be loaded.

    This function uses the `get_ancestors` and `get_descendants` functions to load
    a partial tree. It can load:
    - Only ancestors (using `get_ancestors`)
    - Only descendants (using `get_descendants`)
    - Both ancestors and descendants (using both functions)
    The root of the tree is the person with the specified `person_id`.

    If both `only_ancestors` and `only_descendants` are True at the same time, it
    raises a 400 error.

    The result is a dictionary with the following structure:
    {
        'center': Person object,  # The central person
        'ancestors': [Person objects],  # List of ancestors
        'descendants': [Person objects]  # List of descendants
    }

    This structure is designed to be easily used in the frontend to display the
    family tree around the central person.
    and optionally specifying if only ancestors or descendants should be loaded.

    Args:
        db: The database session.
        person_id: The ID of the central person.
        depth: The maximum depth of the tree to load.
        only_ancestors: If True, only ancestors will be loaded.
        only_descendants: If True, only descendants will be loaded.

    Returns:
        A dictionary containing the partial tree data.
    """
    try:
        if depth <= 0:
            return []

        partial_tree = {'center': get_person_by_id(db, person_id), 'ancestors': [], 'descendants': []}

        if only_ancestors and not only_descendants:
            partial_tree['ancestors'] = get_ancestors(db, person_id, depth)
        elif only_descendants and not only_ancestors:
            partial_tree['descendants'] = get_descendants(db, person_id, depth)
        elif not only_ancestors and not only_descendants:
            partial_tree['ancestors'] = get_ancestors(db, person_id, depth)
            partial_tree['descendants'] = get_descendants(db, person_id, depth)
        elif only_ancestors and only_descendants:
            raise HTTPException(
                status_code=400,
                detail="Cannot request only ancestors and only descendants at the same time."
            )
        else:
             raise HTTPException(
                status_code=400,
                detail="Invalid combination of only_ancestors and only_descendants."
            )
        return partial_tree
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))


def get_descendants(db: Session, person_id: int, depth: int):
    """
    Retrieves the descendants of a person up to a certain depth.

    This function uses a Breadth-First Search (BFS) algorithm to traverse
    the family tree downwards from the given person. It starts from the person
    specified by `person_id` and traverses down the tree through 'parent'
    relationships.

    The function maintains a queue of (person_id, current_depth) pairs. It
    iteratively processes the queue, exploring each person's children and
    adding them to the queue if the current depth is less than the specified
    `depth`.

    Args:
        db: The database session.
        person_id: The ID of the person.
        depth: The maximum depth to traverse downwards.

    Returns:
        A list of Person objects representing the descendants.
    """
    """
    Retrieves the descendants of a person up to a certain depth.
    Args:
        db: The database session.
        person_id: The ID of the person.
        depth: The maximum depth to traverse.
    Returns:
        A list of Person objects representing the descendants.
    """
    try:
        if depth <= 0:
            return []

        descendants = []
        queue = [(person_id, 0)]  # (person_id, current_depth)

        while queue:
            current_person_id, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            person_obj = get_person_by_id(db, current_person_id)
            relationships = db.query(relationship.Relationship).filter(relationship.Relationship.person1_id == current_person_id, relationship.Relationship.rel_type == 'parent').all()

            for rel in relationships:
                if rel.person2_id not in [p.id for p in descendants]:
                    descendants.append(get_person_by_id(db, rel.person2_id))
                queue.append((rel.person2_id, current_depth + 1))
        return descendants

    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))


def get_extended_family(db: Session, person_id: int, depth: int):
    """
    Retrieves the extended family of a person up to a certain depth.

    This function uses a Breadth-First Search (BFS) algorithm to traverse
    the family tree upwards from the given person, and then returns all the persons
    found in that traversal.

    It starts from the person specified by `person_id` and traverses up the tree
    through 'parent' relationships.

    The function maintains a queue of (person_id, current_depth) pairs. It
    iteratively processes the queue, exploring each person's parents and
    adding them to the queue if the current depth is less than the specified
    `depth`.

    Args:
        db: The database session.
        person_id: The ID of the person.
        depth: The maximum depth to traverse.
    Returns:
        A list of Person objects representing the extended family.
    """
    """
    Retrieves the extended family of a person up to a certain depth.
    Args:
        db: The database session.
        person_id: The ID of the person.
        depth: The maximum depth to traverse.
    Returns:
        A list of Person objects representing the extended family.
    """
    try:

        if depth <= 0:
            return []

        extended_family = []
        queue = [(person_id, 0)]

        while queue:
            current_person_id, current_depth = queue.pop(0)        
            people = db.query(person.Person).all()
            
            if not any(p.id == current_person_id for p in people):
                continue

            ancestors = set()
            if current_depth >= depth:
                continue
            person_obj = get_person_by_id(db, current_person_id)
            relationships = db.query(relationship.Relationship).filter(relationship.Relationship.person2_id == current_person_id, relationship.Relationship.rel_type == 'parent').all()

            for rel in relationships:
                ancestors.add(rel.person1_id)
                queue.append((rel.person1_id, current_depth + 1))
        return [get_person_by_id(db, ancestor_id) for ancestor_id in ancestors]

    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))

def get_related(db: Session, person_id: int, depth: int):
    """
    Retrieves the related people of a person up to a certain depth.

    This function uses a Breadth-First Search (BFS) algorithm to traverse
    the family tree from the given person. It explores both directions of
    relationships (person1 and person2) and iteratively adds related people
    to the queue, up to the specified `depth`.

    The function maintains a queue of (person_id, current_depth) pairs. It
    iteratively processes the queue, exploring each person's relationships.
    For each relationship, it determines the other person involved and adds
    them to the queue if they haven't already been visited and if the
    current depth is less than the specified `depth`.

    This function will find all related people, including parents, children,
    spouses, siblings, and other in-laws.

    Args:
        db: The database session.
        person_id: The ID of the person.
        depth: The maximum depth to traverse.
    Returns:
        A list of Person objects representing the related people.
    """
    """
    Retrieves the related people of a person up to a certain depth.
    Args:
        db: The database session.
        person_id: The ID of the person.
        depth: The maximum depth to traverse.
    Returns:
        A list of Person objects representing the related people.
    """
    try:
        if depth <= 0:
            return []

        related_people = []
        queue = [(person_id, 0)]  # (person_id, current_depth)

        while queue:
            current_person_id, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            person_obj = get_person_by_id(db, current_person_id)

            # Find relationships where this person is either person1 or person2
            relationships = db.query(relationship.Relationship).filter(
                (relationship.Relationship.person1_id == current_person_id) | (relationship.Relationship.person2_id == current_person_id)
            ).all()

            for rel in relationships:
                # Determine the other person involved in the relationship
                other_person_id = rel.person2_id if rel.person1_id == current_person_id else rel.person1_id
                if other_person_id not in [p.id for p in related_people]:
                    related_people.append(get_person_by_id(db, other_person_id))
                queue.append((other_person_id, current_depth + 1))
        return related_people

    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))

def get_all_citations(db: Session, page: int = 1, page_size: int = 10, order_by: str = 'id', order_direction: str = 'asc', source_id: int = None, person_id: int = None, description: str = None, fields: list = None):
    """
    Retrieves all citations from the database with pagination, sorting and filtering.

    Args:
        db: The database session.
        page: The page number to retrieve.
        page_size: The number of items per page.
        order_by: The field to order by.
        order_direction: The direction to order (asc or desc). Default is asc.
        source_id: Filter by source ID.
        person_id: Filter by person ID.
        description: Filter by description (partial match).

    Returns:
        A dictionary containing the list of citations for the current page,
        total number of items, current page, page size, and total pages.
    """
    try:
        # Calculate the total number of items
        query = db.query(citation.Citation)

        if fields:
            query = query.options(load_only(*fields))

        if source_id:
            query = query.filter(citation.Citation.source_id == source_id)
        if person_id:
            query = query.filter(citation.Citation.person_id == person_id)
        if description:
            query = query.filter(citation.Citation.description.ilike(f"%{description}%"))

        total_items = query.count()

        # Calculate the offset for the current page
        offset = (page - 1) * page_size
        
        # Retrieve the items for the current page
        query = db.query(citation.Citation)

        # Add sorting if order_by is provided
        valid_order_by_columns = ['id', 'source_id', 'person_id', 'description'] # Update the valid columns
        if order_by in valid_order_by_columns:
            order_column = getattr(citation.Citation, order_by)

            if order_direction == 'desc':
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))

        else:
            query = query.order_by(citation.Citation.id.asc())
        results = query.offset(offset).limit(page_size).all()

        if fields:
          results = [
            {field: getattr(item, field) for field in fields if hasattr(item, field)}
            for item in results
            ]
        else:
          results = query.offset(offset).limit(page_size).all()

        for item in results:
          if not isinstance(item, dict):
            item.__dict__["_links"] = {
                "source": urljoin(str(request.base_url), f"/api/sources/{item.source_id}"),
                "person": urljoin(str(request.base_url), f"/api/people/{item.person_id}"),
            for item in results
            ]

        return {
            "results": results,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_items + page_size - 1) // page_size
        }
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def get_citation_by_id(db: Session, citation_id: int):
    try:
        citation_obj = db.query(citation.Citation).filter(
            citation.Citation.id == citation_id
        ).first()
        if citation_obj is None:

            raise HTTPException(status_code=404, detail="Citation not found")
        query = db.query(citation.Citation).filter(citation.Citation.id == citation_id)
        if fields:
            query = query.options(load_only(*fields))
        citation_obj = query.first()
        if fields: return {field: getattr(citation_obj, field) for field in fields if hasattr(citation_obj, field)}
        return citation_obj
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))


def create_citation(db: Session, citation_data: dict):
    try:
        new_citation = citation.Citation(**citation_data)
        db.add(new_citation)
        db.commit()
        db.refresh(new_citation)
        return new_citation
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def update_citation(db: Session, citation_id: int, citation_data: dict, fields: list = None):
    try:
        db.query(citation.Citation).filter(citation.Citation.id == citation_id).update(citation_data)
        db.commit()
        return get_citation_by_id(db, citation_id)
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def delete_citation(db: Session, citation_id: int):
    try:
        db.query(citation.Citation).filter(citation.Citation.id == citation_id).delete()
        db.commit()
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def get_all_sources(db: Session, page: int = 1, page_size: int = 10, order_by: str = 'id', order_direction: str = 'asc', title: str = None, author: str = None, fields: list = None):
    """
    Retrieves all sources from the database with pagination.
    
    Args:
        db: The database session.
        page: The page number to retrieve.
        page_size: The number of items per page.
        order_by: The field to order by.
        name: Filter by name (partial match).
        gender: Filter by gender.
        birth_date: Filter by birth date.
        death_date: Filter by death date.
        order_direction: The direction to order (asc or desc). Default is asc.
        
    Returns:
        A dictionary containing the list of sources for the current page,
        total number of items, current page, page size, and total pages.
    """
    try:
        # Calculate the total number of items
        total_items = db.query(source.Source).count()
        
        # Calculate the total number of pages
        total_pages = (total_items + page_size - 1) // page_size
        # Calculate the offset for the current page
        offset = (page - 1) * page_size        

        # Add the fields param to the query
        if fields:
            query = query.options(load_only(*fields))
        
        # Retrieve the items for the current page
        query = db.query(source.Source)
        
        if title:
            query = query.filter(source.Source.title.ilike(f"%{title}%"))
        if author:
            query = query.filter(source.Source.author.ilike(f"%{author}%"))        

        # Add sorting if order_by is provided 
        valid_order_by_columns = ['id', 'title', 'author', 'publication_date']
        if order_by in valid_order_by_columns:

            order_column = getattr(source.Source, order_by)

            if order_direction == 'desc':
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
        else:
            # Default sort is by id ascending
            query = query.order_by(source.Source.id.asc())        

        results = query.offset(offset).limit(page_size).all()
        return {
            "results": [
                {field: getattr(item, field) for field in fields if hasattr(item, field)}
                for item in results
            ] if fields else results,
            "results": results,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

        

    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))


def get_source_by_id(db: Session, source_id: int):
    
    try:


        query = db.query(source.Source).filter(source.Source.id == source_id)
        if fields:
            query = query.options(load_only(*fields))
        source_obj = db.query(source.Source).filter(
            source.Source.id == source_id
        ).first()
        if source_obj is None:
            raise HTTPException(status_code=404, detail="Source not found")
        source_obj.__dict__["_links"] = {}
            raise HTTPException(status_code=404, detail="Source not found")
        return source_obj
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))


    try:
        new_source = source.Source(**source_data)
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        return new_source
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))


def create_source(db: Session, source_data: dict):

    try:
        new_source = source.Source(**source_data)
        db.add(new_source)


def update_source(db: Session, source_id: int, source_data: dict):
    try:
        db.query(source.Source).filter(source.Source.id == source_id).update(source_data)
        db.commit()
        return get_source_by_id(db, source_id)
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def delete_source(db: Session, source_id: int):
    try:
        db.query(source.Source).filter(source.Source.id == source_id).delete()
        db.commit()
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def get_all_media(db: Session, page: int = 1, page_size: int = 10, order_by: str = 'id', order_direction: str = 'asc', file_name: str = None, file_type: str = None, description: str = None, fields: list = None):
    """
    Retrieves all media items from the database with pagination.
    
    Args:
        db: The database session.
        page: The page number to retrieve.
        page_size: The number of items per page.
        order_by: The field to order by.
        order_direction: The direction to order (asc or desc). Default is asc.


    Returns:
        A dictionary containing the list of media items for the current page,
        total number of items, current page, page size, and total pages.
    """
    try:
        # Calculate the total number of items
        total_items = db.query(media.Media).count()
        
        # Calculate the total number of pages
        total_pages = (total_items + page_size - 1) // page_size
        
        # Calculate the offset for the current page
        offset = (page - 1) * page_size
        
        # Retrieve the items for the current page
        query = db.query(media.Media)
            query = query.options(load_only(*fields))
        
        # Add filtering
        if file_name:
            query = query.filter(media.Media.file_name.ilike(f"%{file_name}%"))


        if file_name:
            query = query.filter(media.Media.file_name.ilike(f"%{file_name}%"))
        if file_type:
            query = query.filter(media.Media.file_type.ilike(f"%{file_type}%"))
        if description:
            query = query.filter(media.Media.description.ilike(f"%{description}%"))

        # Add sorting if order_by is provided
        valid_order_by_columns = ['id', 'file_name', 'file_type', 'description']
        if order_by in valid_order_by_columns:

            order_column = getattr(media.Media, order_by)

            if order_direction == 'desc':
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
        else: query = query.order_by(media.Media.id.asc())
        
        results = query.offset(offset).limit(page_size).all()

        if fields:
            
            results = [
                {field: getattr(item, field) for field in fields if hasattr(item, field)}
                for item in results
            ]

        return {
            "results": results,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
        }
        
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))


def get_media_by_id(db: Session, media_id: int, fields: list = None):
    try:
        query = db.query(media.Media).filter(media.Media.id == media_id)
        if fields:
            query = query.options(load_only(*fields))

        media_obj = query.first()
        if media_obj is None:
            raise HTTPException(status_code=404, detail="Media not found")
        if fields:
            return {field: getattr(media_obj, field) for field in fields if hasattr(media_obj, field)}
        media_obj.__dict__["_links"] = {}

        
        return media_obj
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_media(db: Session, media_data: dict):
    try:
        new_media = media.Media(**media_data)
        db.add(new_media)
        db.commit()
        db.refresh(new_media)
        return new_media
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def update_media(db: Session, media_id: int, media_data: dict, fields: list = None):
    try:        
        db.query(media.Media).filter(media.Media.id == media_id).update(media_data)
        db.commit()
        return get_media_by_id(db, media_id, fields)
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def delete_media(db: Session, media_id: int):
    try:
        db.query(media.Media).filter(media.Media.id == media_id).delete()
        db.commit()
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def get_all_relationships(db: Session, request: Request, page: int = 1, page_size: int = 10, order_by: str = 'id', order_direction: str = 'asc', type: str = None, person1_id: int = None, person2_id: int = None, fields: list = None):
    """
    Retrieves all relationships from the database with pagination.
    
    Args:
        db: The database session.
        page: The page number to retrieve.
        page_size: The number of items per page.
        order_by: The field to order by.
        order_direction: The direction to order (asc or desc). Default is asc.
        type: filter by relationship type
        person1_id: filter by person 1 id
        person2_id: filter by person 2 id
        
    Returns:
        A dictionary containing the list of relationships for the current page,
        total number of items, current page, page size, and total pages.
    """
    try:
        # Calculate the total number of items
        total_items = db.query(relationship.Relationship).count()
        
        # Calculate the total number of pages
        total_pages = (total_items + page_size - 1) // page_size
        
        # Calculate the offset for the current page
        offset = (page - 1) * page_size
        
        # Retrieve the items for the current page
        query = db.query(relationship.Relationship)

        if fields:
          query = query.options(load_only(*fields))
        

        results = query.offset(offset).limit(page_size).all()

        # adding the _links in the results
        for item in results:
            item.__dict__["_links"] = {
                "person1": urljoin(str(request.base_url), f"/api/people/{item.person1_id}"),
                "person2": urljoin(str(request.base_url), f"/api/people/{item.person2_id}"),
            }

        if type:
            query = query.filter(relationship.Relationship.rel_type == type)
        if person1_id:
            query = query.filter(relationship.Relationship.person1_id == person1_id)
        if person2_id:
            query = query.filter(relationship.Relationship.person2_id == person2_id)
        
        # Add sorting if order_by is provided
        valid_order_by_columns = ['id', 'type', 'person1_id', 'person2_id']
        if order_by in valid_order_by_columns:
          
          order_column = getattr(relationship.Relationship, order_by)
          
          if order_direction == 'desc':
            query = query.order_by(desc(order_column))
          else:
            query = query.order_by(asc(order_column))
        
        if fields:
          results = [
            {field: getattr(item, field) for field in fields if hasattr(item, field)}
            for item in results
            ]
        return {
            "results": results,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))


def get_relationship_by_id(db: Session, request: Request, relationship_id: int, fields: list = None):
    """Retrieves a relationship by its ID."""
    
    try:
        query = db.query(relationship.Relationship).filter(relationship.Relationship.id == relationship_id)


        if fields:
          query = query.options(load_only(*fields))
        relationship_obj = query.first()
        if not relationship_obj:
        # adding the _links
        relationship_obj.__dict__["_links"] = {
            "person1": urljoin(
                str(request.base_url), f"/api/people/{relationship_obj.person1_id}"
            ),
            "person2": urljoin(str(request.base_url), f"/api/people/{relationship_obj.person2_id}"),
        }
          raise HTTPException(status_code=404, detail="Relationship not found")
        if fields:
            return {field: getattr(relationship_obj, field) for field in fields if hasattr(relationship_obj, field)}
        return relationship_obj
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

        raise HTTPException(status_code=500, detail=str(e))


def create_relationship(db: Session, relationship_data: dict):
    try:
        new_relationship = relationship.Relationship(**relationship_data)
        db.add(new_relationship)
        db.commit()
        db.refresh(new_relationship)
        return new_relationship
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def update_relationship(db: Session, relationship_id: int, relationship_data: dict):
    try:
        db.query(relationship.Relationship).filter(relationship.Relationship.id == relationship_id).update(relationship_data)
        db.commit()
        return get_relationship_by_id(db, request, relationship_id, fields=[])
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def delete_relationship(db: Session, relationship_id: int):
    try:
        db.query(relationship.Relationship).filter(relationship.Relationship.id == relationship_id).delete()
        db.commit()
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def get_all_relationship_attributes(db: Session, page: int = 1, page_size: int = 10, order_by: str = 'id', order_direction: str = 'asc', key: str = None, value: str = None, relationship_id: int = None, fields: list = None):
   """
    Retrieves all relationship attributes from the database with pagination and sorting.

    Args:
        db: The database session.
        page: The page number to retrieve.
        page_size: The number of items per page.
        order_by: The field to order by.
        order_direction: The direction to order (asc or desc). Default is asc.

    Returns:
        A dictionary containing the list of relationship attributes, pagination and sorting metadata.
    """
    try:

      query = db.query(relationship_attribute.RelationshipAttribute)
      
      if fields:
          query = query.options(load_only(*fields))

      if key:
          query = query.filter(relationship_attribute.RelationshipAttribute.key.ilike(f"%{key}%"))
          
      if value:
          query = query.filter(relationship_attribute.RelationshipAttribute.value.ilike(f"%{value}%"))
      if relationship_id:
          query = query.filter(relationship_attribute.RelationshipAttribute.relationship_id == relationship_id)
        
        # Calculate the total number of items
        total_items = query.count()

        # Calculate the total number of pages
        
        total_pages = (total_items + page_size - 1) // page_size

        # Calculate the offset for the current page
        offset = (page - 1) * page_size

        # Add sorting if order_by is provided
        valid_order_by_columns = ['id', 'key', 'value', 'relationship_id']
        if order_by in valid_order_by_columns:
          
          order_column = getattr(relationship_attribute.RelationshipAttribute, order_by)
          
          if order_direction == 'desc':
            query = query.order_by(desc(order_column))
          else:
            query = query.order_by(asc(order_column))


      results = query.offset(offset).limit(page_size).all()
      
      if fields:
          results = [
            {field: getattr(item, field) for field in fields if hasattr(item, field)}
            for item in results]
        results = [
            {field: getattr(item, field) for field in fields if hasattr(item, field)}
            for item in results
        ]
        return {

            "results": results,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }    
        
        for item in results:
            if not isinstance(item, dict):
              item.__dict__["_links"] = {
                  "relationship": f"/api/relationships/{item.relationship_id}"
              }
            else: item["_links"] = {
                  "relationship": f"/api/relationships/{item.get('relationship_id')}"
            }
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))

def get_relationship_attribute_by_id(db: Session, relationship_attribute_id: int, fields: list = None):

    
    try:
        query = db.query(relationship_attribute.RelationshipAttribute).filter(relationship_attribute.RelationshipAttribute.id == relationship_attribute_id)

        if fields:
            query = query.options(load_only(*fields))

        relationship_attribute_obj = query.first()

        if relationship_attribute_obj is None:
            raise HTTPException(status_code=404, detail="Relationship attribute not found")
        
        if fields:
            return {field: getattr(relationship_attribute_obj, field) for field in fields if hasattr(relationship_attribute_obj, field)}        
        
        relationship_attribute_obj.__dict__["_links"] = {"relationship": f"/api/relationships/{relationship_attribute_obj.relationship_id}"}


        return relationship_attribute_obj
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))



def create_relationship_attribute(db: Session, relationship_attribute_data: dict):
    try:
        new_relationship_attribute = relationship_attribute.RelationshipAttribute(**relationship_attribute_data)
        db.add(new_relationship_attribute)
        db.commit()
        db.refresh(new_relationship_attribute)
        return new_relationship_attribute
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def update_relationship_attribute(db: Session, relationship_attribute_id: int, relationship_attribute_data: dict):
    
        db.query(relationship_attribute.RelationshipAttribute).filter(
            relationship_attribute.RelationshipAttribute.id == relationship_attribute_id).update(relationship_attribute_data)
        db.query(relationship_attribute.RelationshipAttribute).filter(relationship_attribute.RelationshipAttribute.id == relationship_attribute_id).update(relationship_attribute_data)
        db.commit()    
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def get_all_person_attributes(db: Session, page: int = 1, page_size: int = 10, order_by: str = 'id', order_direction: str = 'asc', key: str = None, value: str = None, fields: list = None):
    """
    Retrieves all person attributes from the database with pagination.

    Args:
    Retrieves all person attributes from the database with pagination, sorting and filtering.

    Args:
        db: The database session.
        page: The page number to retrieve.
        page_size: The number of items per page.
        order_by: The field to order by.
        order_direction: The direction to order (asc or desc). Default is asc.
        key: filter by key (partial match).
        db: The database session.
        page: The page number to retrieve.
        page_size: The number of items per page.
        order_by: The field to order by.
        order_direction: The direction to order (asc or desc). Default is asc.

    Returns:
        A dictionary containing the list of person attributes for the current page,
        total number of items, current page, page size, and total pages.
    """
    try:
        query = db.query(person_attribute.PersonAttribute)

        if fields:
            query = query.options(load_only(*fields))
        if key:
            query = query.filter(person_attribute.PersonAttribute.key.ilike(f"%{key}%"))
        if value:
            query = query.filter(person_attribute.PersonAttribute.value.ilike(f"%{value}%"))
        # Calculate the total number of items
        total_items = query.count()

        # Calculate the total number of pages
        total_pages = (total_items + page_size - 1) // page_size

        # Calculate the offset for the current page
        offset = (page - 1) * page_size

        # Retrieve the items for the current page


        # Add sorting if order_by is provided
        valid_order_by_columns = ['id', 'key', 'value']
        if order_by in valid_order_by_columns:

            order_column = getattr(person_attribute.PersonAttribute, order_by)

            if order_direction == 'desc':
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
        else:
            # Default sort is by id ascending
            query = query.order_by(person_attribute.PersonAttribute.id.asc())
        if fields:
            results = [
                {field: getattr(item, field) for field in fields if hasattr(item, field)}
                for item in query.offset(offset).limit(page_size).all()
            ]
        else: results = query.offset(offset).limit(page_size).all()

        for item in results:
            if not isinstance(item, dict):
                item.__dict__.pop('_sa_instance_state', None)
                
            item_id = item["id"] if isinstance(item, dict) else item.id
            if not "_links" in item:
                item["_links"] = {"person": f"/api/people/{item.person_id}"}

        return {
            "results": results,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
def get_person_attribute(db: Session, person_attribute_id: int, fields: list = None):
    try:
        query = db.query(person_attribute.PersonAttribute).filter(person_attribute.PersonAttribute.id == person_attribute_id)
        if fields:
            query = query.options(load_only(*fields))
            "total_pages": total_pages
        }
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))


        person_attribute_obj = query.first()
        if not person_attribute_obj:
            raise HTTPException(status_code=404, detail="Person attribute not found")

        if not isinstance(person_attribute_obj, dict):
            person_attribute_obj.__dict__.pop('_sa_instance_state', None)
        if not "_links" in person_attribute_obj.__dict__:
            person_attribute_obj.__dict__["_links"] = {"person": f"/api/people/{person_attribute_obj.person_id}"}

        if fields: return {field: getattr(person_attribute_obj, field) for field in fields if hasattr(person_attribute_obj, field)}
        return person_attribute_obj
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_person_attribute(db: Session, person_attribute_data: dict):
    try:
        new_person_attribute = person_attribute.PersonAttribute(**person_attribute_data)
        db.add(new_person_attribute)
        db.commit()
        db.refresh(new_person_attribute)
        return new_person_attribute
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def update_person_attribute(db: Session, person_attribute_id: int, person_attribute_data: dict):
    try:
        db.query(person_attribute.PersonAttribute).filter(
            person_attribute.PersonAttribute.id == person_attribute_id
        ).update(person_attribute_data)
        db.commit()    
        return get_person_attribute_by_id(db, person_attribute_id)
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def delete_person_attribute(db: Session, person_attribute_id: int):
    try:
        db.query(person_attribute.PersonAttribute).filter(person_attribute.PersonAttribute.id == person_attribute_id).delete()
        db.commit()
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
def delete_relationship_attribute(db: Session, relationship_attribute_id: int):
    try:
        db.query(relationship_attribute.RelationshipAttribute).filter(
            relationship_attribute.RelationshipAttribute.id == relationship_attribute_id).delete()
        db.commit()
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def get_all_events(db: Session, page: int = 1, page_size: int = 10, order_by: str = 'id', order_direction: str = 'asc', type: str = None, place: str = None, description: str = None, fields: list = None):
    """
    Retrieves all events from the database with pagination.
    
    Args:
        db: The database session.
        page: The page number to retrieve.
        page_size: The number of items per page.
        order_by: The field to order by.
        order_direction: The direction to order (asc or desc). Default is asc.
        
    Returns:
        A dictionary containing the list of events for the current page,
        total number of items, current page, page size, and total pages.
    """
    try:
        # Calculate the total number of items
        total_items = db.query(event.Event).count()
        
        # Calculate the total number of pages
        total_pages = (total_items + page_size - 1) // page_size
        
        # Calculate the offset for the current page
        offset = (page - 1) * page_size
        
        # Retrieve the items for the current page
        query = db.query(event.Event)

        if fields:
            query = query.options(load_only(*fields))
        
        if type:
            query = query.filter(event.Event.type == type)
        if place:
            query = query.filter(event.Event.place.ilike(f"%{place}%"))
        if description:
            query = query.filter(event.Event.description.ilike(f"%{description}%"))
        

        # Add sorting if order_by is provided
        valid_order_by_columns = ['id', 'type', 'date', 'place', 'description']
        if order_by in valid_order_by_columns:
          
          order_column = getattr(event.Event, order_by)
          
          if order_direction == 'desc':
            query = query.order_by(desc(order_column))
          else:
            query = query.order_by(asc(order_column))
        else:
          # Default sort is by id ascending
          query = query.order_by(event.Event.id.asc())

        if fields:
            results = [
                {field: getattr(item, field) for field in fields if hasattr(item, field)}
                for item in query.offset(offset).limit(page_size).all()
            ]
        else:
            results = query.offset(offset).limit(page_size).all()

        for item in results:
            item.__dict__["_links"] = {}

        return {
            "results": results,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages

        }
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))


def get_event_by_id(db: Session, event_id: int):

    try:
        query = db.query(event.Event).filter(event.Event.id == event_id)
        if fields:
            query = query.options(load_only(*fields))
        event_obj = query.first()
        if event_obj is None:
            raise HTTPException(status_code=404, detail="Event not found")
        if fields:
            return {field: getattr(event_obj, field) for field in fields if hasattr(event_obj, field)}
        else:
            event_obj.__dict__["_links"] = {}
            return event_obj
    except SQLAlchemyError as e:

        raise HTTPException(status_code=500, detail=str(e))


def create_event(db: Session, event_data: dict):
    try:
        new_event = event.Event(**event_data)
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        return new_event
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def update_event(db: Session, event_id: int, event_data: dict, fields: list = None):
    try:
        db.query(event.Event).filter(event.Event.id == event_id).update(event_data)
        db.commit()
        return get_event_by_id(db, event_id)
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def delete_event(db: Session, event_id: int):
    try:
        db.query(event.Event).filter(event.Event.id == event_id).delete()
        db.commit()
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def get_all_people(db: Session, page: int = 1, page_size: int = 10, order_by: str = 'id', order_direction: str = 'asc', name: str = None, gender: str = None, birth_date: date = None, death_date: date = None, fields: list = None):
    """
    Retrieves all people from the database with pagination.
    
    Args:
        db: The database session.
        page: The page number to retrieve.
        page_size: The number of items per page.
        order_by: The field to order by.
        order_direction: The direction to order (asc or desc). Default is asc.
        
    Returns:
        A dictionary containing the list of people for the current page,
        total number of items, current page, page size, and total pages.
    """
    try:
        # Calculate the total number of items
        query = db.query(person.Person)

        if fields:
            query = query.options(load_only(*fields))
        total_items = query.count()
        
        # Calculate the total number of pages
        total_pages = (total_items + page_size - 1) // page_size
        offset = (page - 1) * page_size 
        
        # Retrieve the items for the current page
        query = db.query(person.Person)

        # Add sorting if order_by is provided
        valid_order_by_columns = ['id', 'name', 'gender', 'birth_date', 'death_date']

        if order_by in valid_order_by_columns:    
          
          order_column = getattr(person.Person, order_by)
          
          if order_direction == 'desc':
            query = query.order_by(desc(order_column))
          else:
            query = query.order_by(asc(order_column))
        else:
            # Default sort is by id ascending
            if name:
                query = query.filter(person.Person.name.ilike(f"%{name}%") )
            if gender:
                query = query.filter(person.Person.gender == gender)
            if birth_date:
                query = query.filter(person.Person.birth_date == birth_date)
            if death_date:
                query = query.filter(person.Person.death_date == death_date)
            query = query.order_by(person.Person.id.asc())
            
        if fields:
          results = [
            {field: getattr(item, field) for field in fields if hasattr(item, field)}
            for item in query.offset(offset).limit(page_size).all()
            ]
        else:
          results = query.offset(offset).limit(page_size).all()
        
        return { "results": results, "total_items": total_items,
            "page": page,
            "page_size": page_size,
        }







    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_person_by_id(db: Session, person_id: int, fields: list = None):
    try:
        person_obj = db.query(person.Person).filter(person.Person.id == person_id).first()
        if person_obj is None:
            raise HTTPException(status_code=404, detail="Person not found")
        return person_obj




    except SQLAlchemyError as e:




def create_person(db: Session, person_data: dict):
    try:
        new_person = person.Person(**person_data)
        db.add(new_person)
        db.commit()
        db.refresh(new_person)
        return new_person
    except SQLAlchemyError as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
def get_person(db: Session, person_id: int, fields: list = None):
  try:
      person_obj = db.query(person.Person).filter(person.Person.id == person_id).first()
      if person_obj is None:
          raise HTTPException(status_code=404, detail="Person not found")

      response_data = {field: getattr(person_obj, field) for field in fields} if fields else person_obj.__dict__
      
      if "_sa_instance_state" in response_data:
          del response_data["_sa_instance_state"]

      # Add links to related resources
      response_data["_links"] = {
          "relationships": f"/api/relationships?person_id={person_id}",
          "attributes": f"/api/person_attributes?person_id={person_id}",
      }
      return response_data

  except SQLAlchemyError as e:
      db.rollback()
      raise HTTPException(status_code=500, detail=str(e))










