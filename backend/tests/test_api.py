# backend/tests/test_api.py
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app import app, create_tables
from backend.app.models import Base
from backend.app.db_init import populate_db


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="module")
def test_app():
    """
    This fixture is responsible for creating the database tables and populate the db with the initial data.
    """
    db = TestingSessionLocal()
    create_tables(db)
    populate_db(db)
    yield
    Base.metadata.drop_all(bind=engine)


def test_get_all_users(test_app):
    response = client.get("/api/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0


def test_get_user_by_id(test_app):
    response = client.get("/api/users/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_create_user(test_app):
    user_data = {"username": "testuser", "password_hash": "testpassword", "role": "testrole", "created_at": "2024-01-01T00:00:00", "last_login": "2024-01-01T00:00:00"}
    response = client.post("/api/users", json=user_data)
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"


def test_get_all_people(test_app):
    response = client.get("/api/people")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0


def test_get_person_by_id(test_app):
    response = client.get("/api/people/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_create_person(test_app):
    person_data = {"first_name": "testfirst", "last_name": "testlast", "gender": "M", "created_by": 1, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"}
    response = client.post("/api/people", json=person_data)
    assert response.status_code == 200
    assert response.json()["first_name"] == "testfirst"


def test_get_all_person_attributes(test_app):
    response = client.get("/api/person_attributes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_person_attribute_by_id(test_app):
    response = client.get("/api/person_attributes/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_create_person_attribute(test_app):
    person_attribute_data = {"person_id": 1, "key": "testkey", "value": "testvalue"}
    response = client.post("/api/person_attributes", json=person_attribute_data)
    assert response.status_code == 200
    assert response.json()["key"] == "testkey"


def test_update_person_attribute(test_app):
    # First, create a person attribute
    person_attribute_data = {"person_id": 1, "key": "updatetestkey", "value": "updatetestvalue"}
    create_response = client.post("/api/person_attributes", json=person_attribute_data)
    assert create_response.status_code == 200
    person_attribute_id = create_response.json()["id"]

    # Then, update the created person attribute
    update_data = {"person_id": 1, "key": "updatedkey", "value": "updatedvalue"}
    update_response = client.put(
        f"/api/person_attributes/{person_attribute_id}", json=update_data
    )
    assert update_response.status_code == 200
    assert update_response.json()["key"] == "updatedkey"
    assert update_response.json()["value"] == "updatedvalue"


def test_delete_person_attribute(test_app):
    person_attribute_data = {"person_id": 1, "key": "deletetestkey", "value": "deletetestvalue"}
    create_response = client.post("/api/person_attributes", json=person_attribute_data)
    assert create_response.status_code == 200
    person_attribute_id = create_response.json()["id"]

    response = client.delete(f"/api/person_attributes/{person_attribute_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "PersonAttribute deleted"
from backend.app import get_db


def test_get_all_relationships(test_app):
    response = client.get("/api/relationships")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_relationship_by_id(test_app):
    response = client.get("/api/relationships/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_create_relationship(test_app):
    relationship_data = {"person1_id": 1, "person2_id": 2, "rel_type": "testtype", "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"}
    response = client.post("/api/relationships", json=relationship_data)
    assert response.status_code == 200
    assert response.json()["rel_type"] == "testtype"


def test_update_relationship(test_app):
    # First, create a relationship
    relationship_data = {"person1_id": 1, "person2_id": 2, "rel_type": "updatetesttype", "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"}
    create_response = client.post("/api/relationships", json=relationship_data)
    assert create_response.status_code == 200
    relationship_id = create_response.json()["id"]

    # Then, update the created relationship
    update_data = {"person1_id": 1, "person2_id": 2, "rel_type": "updatedtype", "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"}
    update_response = client.put(
        f"/api/relationships/{relationship_id}", json=update_data
    )
    assert update_response.status_code == 200
    assert update_response.json()["rel_type"] == "updatedtype"


def test_delete_relationship(test_app):
    relationship_data = {"person1_id": 1, "person2_id": 2, "rel_type": "deletetesttype", "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"}
    create_response = client.post("/api/relationships", json=relationship_data)
    assert create_response.status_code == 200
    relationship_id = create_response.json()["id"]

    response = client.delete(f"/api/relationships/{relationship_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Relationship deleted"


def test_get_all_relationship_attributes(test_app):
    response = client.get("/api/relationship_attributes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_relationship_attribute_by_id(test_app):
    response = client.get("/api/relationship_attributes/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_create_relationship_attribute(test_app):
    relationship_attribute_data = {"relationship_id": 1, "key": "testkey", "value": "testvalue"}
    response = client.post("/api/relationship_attributes", json=relationship_attribute_data)
    assert response.status_code == 200
    assert response.json()["key"] == "testkey"


def test_update_relationship_attribute(test_app):
    # First, create a relationship attribute
    relationship_attribute_data = {"relationship_id": 1, "key": "updatetestkey", "value": "updatetestvalue"}
    create_response = client.post("/api/relationship_attributes", json=relationship_attribute_data)
    assert create_response.status_code == 200
    relationship_attribute_id = create_response.json()["id"]

    # Then, update the created relationship attribute
    update_data = {"relationship_id": 1, "key": "updatedkey", "value": "updatedvalue"}
    update_response = client.put(
        f"/api/relationship_attributes/{relationship_attribute_id}", json=update_data
    )
    assert update_response.status_code == 200
    assert update_response.json()["key"] == "updatedkey"
    assert update_response.json()["value"] == "updatedvalue"


def test_delete_relationship_attribute(test_app):
    relationship_attribute_data = {"relationship_id": 1, "key": "deletetestkey", "value": "deletetestvalue"}
    create_response = client.post("/api/relationship_attributes", json=relationship_attribute_data)
    assert create_response.status_code == 200
    relationship_attribute_id = create_response.json()["id"]

    response = client.delete(f"/api/relationship_attributes/{relationship_attribute_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "RelationshipAttribute deleted"

def test_get_all_media(test_app):
    response = client.get("/api/media")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_media_by_id(test_app):
    response = client.get("/api/media/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_create_media(test_app):
    media_data = {"person_id": 1, "media_type": "testtype", "file_path": "/test/path", "title": "testtitle", "description": "testdescription", "uploaded_at": "2024-01-01T00:00:00"}
    response = client.post("/api/media", json=media_data)
    assert response.status_code == 200
    assert response.json()["title"] == "testtitle"


def test_update_media(test_app):
    # First, create a media
    media_data = {"person_id": 1, "media_type": "updatetesttype", "file_path": "/test/path", "title": "updatetesttitle", "description": "updatetestdescription", "uploaded_at": "2024-01-01T00:00:00"}
    create_response = client.post("/api/media", json=media_data)
    assert create_response.status_code == 200
    media_id = create_response.json()["id"]

    # Then, update the created media
    update_data = {"person_id": 1, "media_type": "updatedtype", "file_path": "/updated/path", "title": "updatedtitle", "description": "updateddescription", "uploaded_at": "2024-01-01T00:00:00"}
    update_response = client.put(
        f"/api/media/{media_id}", json=update_data
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "updatedtitle"
    assert update_response.json()["description"] == "updateddescription"


def test_delete_media(test_app):
    media_data = {"person_id": 1, "media_type": "deletetesttype", "file_path": "/test/path", "title": "deletetesttitle", "description": "deletetestdescription", "uploaded_at": "2024-01-01T00:00:00"}
    create_response = client.post("/api/media", json=media_data)
    assert create_response.status_code == 200
    media_id = create_response.json()["id"]

    response = client.delete(f"/api/media/{media_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Media deleted"

def test_get_all_events(test_app):
    response = client.get("/api/events")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_event_by_id(test_app):
    response = client.get("/api/events/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_create_event(test_app):
    event_data = {"person_id": 1, "event_type": "testtype", "date": "2024-01-01", "place": "testplace", "description": "testdescription", "created_at": "2024-01-01T00:00:00"}
    response = client.post("/api/events", json=event_data)
    assert response.status_code == 200
    assert response.json()["event_type"] == "testtype"


def test_update_event(test_app):
    # First, create a event
    event_data = {"person_id": 1, "event_type": "updatetesttype", "date": "2024-01-01", "place": "testplace", "description": "testdescription", "created_at": "2024-01-01T00:00:00"}
    create_response = client.post("/api/events", json=event_data)
    assert create_response.status_code == 200
    event_id = create_response.json()["id"]

    # Then, update the created event
    update_data = {"person_id": 1, "event_type": "updatedtype", "date": "2024-01-02", "place": "updatedplace", "description": "updateddescription", "created_at": "2024-01-01T00:00:00"}
    update_response = client.put(
        f"/api/events/{event_id}", json=update_data
    )
    assert update_response.status_code == 200
    assert update_response.json()["event_type"] == "updatedtype"
    assert update_response.json()["place"] == "updatedplace"
    assert update_response.json()["description"] == "updateddescription"


def test_delete_event(test_app):
    event_data = {"person_id": 1, "event_type": "deletetesttype", "date": "2024-01-01", "place": "testplace", "description": "testdescription", "created_at": "2024-01-01T00:00:00"}
    create_response = client.post("/api/events", json=event_data)
    assert create_response.status_code == 200
    event_id = create_response.json()["id"]

    response = client.delete(f"/api/events/{event_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Event deleted"

def test_get_all_sources(test_app):
    response = client.get("/api/sources")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_source_by_id(test_app):
    response = client.get("/api/sources/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_create_source(test_app):
    source_data = {"title": "testtitle", "author": "testauthor", "publication_info": "testpublication", "url": "testurl", "notes": "testnotes", "created_at": "2024-01-01T00:00:00"}
    response = client.post("/api/sources", json=source_data)
    assert response.status_code == 200
    assert response.json()["title"] == "testtitle"


def test_update_source(test_app):
    # First, create a source
    source_data = {"title": "updatetesttitle", "author": "updatetestauthor", "publication_info": "updatetestpublication", "url": "updatetesturl", "notes": "updatetestnotes", "created_at": "2024-01-01T00:00:00"}
    create_response = client.post("/api/sources", json=source_data)
    assert create_response.status_code == 200
    source_id = create_response.json()["id"]

    # Then, update the created source
    update_data = {"title": "updatedtitle", "author": "updatedauthor", "publication_info": "updatedpublication", "url": "updatedurl", "notes": "updatednotes", "created_at": "2024-01-01T00:00:00"}
    update_response = client.put(
        f"/api/sources/{source_id}", json=update_data
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "updatedtitle"
    assert update_response.json()["author"] == "updatedauthor"
    assert update_response.json()["publication_info"] == "updatedpublication"
    assert update_response.json()["url"] == "updatedurl"
    assert update_response.json()["notes"] == "updatednotes"


def test_delete_source(test_app):
    source_data = {"title": "deletetesttitle", "author": "deletetestauthor", "publication_info": "deletetestpublication", "url": "deletetesturl", "notes": "deletetestnotes", "created_at": "2024-01-01T00:00:00"}
    create_response = client.post("/api/sources", json=source_data)
    assert create_response.status_code == 200
    source_id = create_response.json()["id"]

    response = client.delete(f"/api/sources/{source_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Source deleted"

def test_get_all_citations(test_app):
    response = client.get("/api/citations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_citation_by_id(test_app):
    response = client.get("/api/citations/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_create_citation(test_app):
    citation_data = {"source_id": 1, "person_id": 1, "citation_text": "testcitation", "page_number": "testpage", "created_at": "2024-01-01T00:00:00"}
    response = client.post("/api/citations", json=citation_data)
    assert response.status_code == 200
    assert response.json()["citation_text"] == "testcitation"


def test_update_citation(test_app):
    # First, create a citation
    citation_data = {"source_id": 1, "person_id": 1, "citation_text": "updatetestcitation", "page_number": "testpage", "created_at": "2024-01-01T00:00:00"}
    create_response = client.post("/api/citations", json=citation_data)
    assert create_response.status_code == 200
    citation_id = create_response.json()["id"]

    # Then, update the created citation
    update_data = {"source_id": 1, "person_id": 1, "citation_text": "updatedcitation", "page_number": "updatedpage", "created_at": "2024-01-01T00:00:00"}
    update_response = client.put(
        f"/api/citations/{citation_id}", json=update_data
    )
    assert update_response.status_code == 200
    assert update_response.json()["citation_text"] == "updatedcitation"
    assert update_response.json()["page_number"] == "updatedpage"


def test_delete_citation(test_app):
    citation_data = {"source_id": 1, "person_id": 1, "citation_text": "deletetestcitation", "page_number": "testpage", "created_at": "2024-01-01T00:00:00"}
    create_response = client.post("/api/citations", json=citation_data)
    assert create_response.status_code == 200
    citation_id = create_response.json()["id"]

    response = client.delete(f"/api/citations/{citation_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Citation deleted"
