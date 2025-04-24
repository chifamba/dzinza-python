from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models import user, person, person_attribute, relationship, relationship_attribute, media, event, source, citation
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


def get_all_citations(db: Session):
    try:
        return db.query(citation.Citation).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_citation_by_id(db: Session, citation_id: int):
    try:
        citation_obj = db.query(citation.Citation).filter(
            citation.Citation.id == citation_id
        ).first()
        if citation_obj is None:
            raise HTTPException(status_code=404, detail="Citation not found")
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


def update_citation(db: Session, citation_id: int, citation_data: dict):
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


def get_all_sources(db: Session):
    try:
        return db.query(source.Source).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_source_by_id(db: Session, source_id: int):
    try:
        source_obj = db.query(source.Source).filter(
            source.Source.id == source_id
        ).first()
        if source_obj is None:
            raise HTTPException(status_code=404, detail="Source not found")
        return source_obj
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_source(db: Session, source_data: dict):
    try:
        new_source = source.Source(**source_data)
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        return new_source
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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


def get_all_media(db: Session):
    try:
        return db.query(media.Media).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_media_by_id(db: Session, media_id: int):
    try:
        media_obj = db.query(media.Media).filter(
            media.Media.id == media_id
        ).first()
        if media_obj is None:
            raise HTTPException(status_code=404, detail="Media not found")
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


def update_media(db: Session, media_id: int, media_data: dict):
    try:
        db.query(media.Media).filter(media.Media.id == media_id).update(media_data)
        db.commit()
        return get_media_by_id(db, media_id)
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


def get_all_relationships(db: Session):
    try:
        return db.query(relationship.Relationship).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_relationship_by_id(db: Session, relationship_id: int):
    try:
        relationship_obj = db.query(relationship.Relationship).filter(
            relationship.Relationship.id == relationship_id
        ).first()
        if relationship_obj is None:
            raise HTTPException(status_code=404, detail="Relationship not found")
        return relationship_obj
    except SQLAlchemyError as e:
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
        return get_relationship_by_id(db, relationship_id)
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

def get_all_relationship_attributes(db: Session):
    try:
        return db.query(relationship_attribute.RelationshipAttribute).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_relationship_attribute_by_id(db: Session, relationship_attribute_id: int):
    try:
        relationship_attribute_obj = db.query(relationship_attribute.RelationshipAttribute).filter(
            relationship_attribute.RelationshipAttribute.id == relationship_attribute_id
        ).first()
        if relationship_attribute_obj is None:
            raise HTTPException(status_code=404, detail="Relationship attribute not found")
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
    try:
        db.query(relationship_attribute.RelationshipAttribute).filter(relationship_attribute.RelationshipAttribute.id == relationship_attribute_id).update(relationship_attribute_data)
        db.commit()
        return get_relationship_attribute_by_id(db, relationship_attribute_id)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def get_all_person_attributes(db: Session):
    try:
        return db.query(person_attribute.PersonAttribute).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_person_attribute_by_id(db: Session, person_attribute_id: int):
    try:
        person_attribute_obj = db.query(person_attribute.PersonAttribute).filter(
            person_attribute.PersonAttribute.id == person_attribute_id
        ).first()
        if person_attribute_obj is None:
            raise HTTPException(status_code=404, detail="Person attribute not found")
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


def get_all_events(db: Session):
    try:
        return db.query(event.Event).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_event_by_id(db: Session, event_id: int):
    try:
        event_obj = db.query(event.Event).filter(
            event.Event.id == event_id
        ).first()
        if event_obj is None:
            raise HTTPException(status_code=404, detail="Event not found")
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


def update_event(db: Session, event_id: int, event_data: dict):
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

def get_all_people(db: Session):
    try:
        return db.query(person.Person).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_person_by_id(db: Session, person_id: int):
    try:
        person_obj = db.query(person.Person).filter(person.Person.id == person_id).first()
        if person_obj is None:
            raise HTTPException(status_code=404, detail="Person not found")
        return person_obj
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

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