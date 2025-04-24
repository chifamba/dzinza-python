# backend/tests/test_api.py
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app import app, create_tables, get_db
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


def test_get_all_people_no_pagination(test_app):
    response = client.get("/api/people")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_items" in response.json()
    assert "page" in response.json()
    assert "page_size" in response.json()
    assert "total_pages" in response.json()
    assert isinstance(response.json()["results"], list)
    assert len(response.json()["results"]) > 0

def test_get_all_people_with_pagination(test_app):
    response = client.get("/api/people?page=1&page_size=2")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_items" in response.json()
    assert "page" in response.json()
    assert "page_size" in response.json()
    assert "total_pages" in response.json()
    assert len(response.json()["results"]) == 2


def test_get_person_by_id(test_app):
    response = client.get("/api/people/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_create_person(test_app):
    person_data = {"first_name": "testfirst", "last_name": "testlast", "gender": "M", "created_by": 1, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"}
    response = client.post("/api/people", json=person_data)
    assert response.status_code == 200
    assert response.json()["first_name"] == "testfirst"


def test_get_all_person_attributes_no_pagination(test_app):
    response = client.get("/api/person_attributes")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_items" in response.json()
    assert "page" in response.json()
    assert "page_size" in response.json()
    assert "total_pages" in response.json()
    assert isinstance(response.json()["results"], list)
    assert len(response.json()["results"]) > 0

def test_get_all_person_attributes_with_pagination(test_app):
    response = client.get("/api/person_attributes?page=1&page_size=2")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_pages" in response.json()
    assert len(response.json()["results"]) == 2


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


def test_get_all_relationships(test_app):
    response = client.get("/api/relationships?page=1&page_size=2")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_items" in response.json()
    assert "page" in response.json()
    assert "page_size" in response.json()
    assert "total_pages" in response.json()
    assert len(response.json()["results"]) == 2


def test_get_all_relationships_no_pagination(test_app):
    response = client.get("/api/relationships")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_pages" in response.json()
    assert isinstance(response.json()["results"], list)


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


def test_get_all_relationship_attributes_no_pagination(test_app):
    response = client.get("/api/relationship_attributes")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_items" in response.json()
    assert "page" in response.json()
    assert "page_size" in response.json()
    assert "total_pages" in response.json()
    assert isinstance(response.json()["results"], list)

def test_get_all_relationship_attributes_with_pagination(test_app):
    response = client.get("/api/relationship_attributes?page=1&page_size=2")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
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
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_items" in response.json()
    assert "page" in response.json()
    assert "page_size" in response.json()
    assert "total_pages" in response.json()
    assert isinstance(response.json()["results"], list)

def test_get_all_media_with_pagination(test_app):
    response = client.get("/api/media?page=1&page_size=2")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert len(response.json()["results"]) == 2

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
    response = client.get("/api/events?page=1&page_size=2")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_items" in response.json()
    assert "page" in response.json()
    assert "page_size" in response.json()
    assert "total_pages" in response.json()
    assert len(response.json()["results"]) == 2

def test_get_all_events_no_pagination(test_app):
    response = client.get("/api/events")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()


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
    response = client.get("/api/citations?page=1&page_size=2")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_items" in response.json()
    assert "page" in response.json()
    assert "page_size" in response.json()
    assert "total_pages" in response.json()
    assert len(response.json()["results"]) == 2

def test_get_all_sources_no_pagination(test_app):
    response = client.get("/api/sources")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()


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

def test_get_all_citations_no_pagination(test_app):
    response = client.get("/api/citations")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_items" in response.json()
    assert "page" in response.json()
    assert "page_size" in response.json()
    assert "total_pages" in response.json()
    assert isinstance(response.json()["results"], list)

def test_get_all_citations_with_pagination(test_app):
    response = client.get("/api/citations?page=1&page_size=2")
    assert len(response.json()["results"]) == 2


def test_get_relationships_and_attributes(test_app):
    response = client.get("/api/people/1/relationships_and_attributes")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

    # Check if the dictionary contains the keys 'person_attributes' and 'relationships'
    assert "person_attributes" in response.json()
    assert "relationships" in response.json()

    # Check if 'person_attributes' is a list and its items are dictionaries
    assert isinstance(response.json()["person_attributes"], list)
    if response.json()["person_attributes"]:
        assert isinstance(response.json()["person_attributes"][0], dict)
        assert "id" in response.json()["person_attributes"][0]
        assert "key" in response.json()["person_attributes"][0]
        assert "value" in response.json()["person_attributes"][0]
        assert "person_id" in response.json()["person_attributes"][0]

    # Check if 'relationships' is a list and its items are dictionaries
    assert isinstance(response.json()["relationships"], list)
    if response.json()["relationships"]:
        assert isinstance(response.json()["relationships"][0], dict)
        assert "id" in response.json()["relationships"][0]
        assert "type" in response.json()["relationships"][0]
        assert "person1_id" in response.json()["relationships"][0]
        assert "person2_id" in response.json()["relationships"][0]
        assert "attributes" in response.json()["relationships"][0]
        if response.json()["relationships"][0]["attributes"]:
            assert isinstance(response.json()["relationships"][0]["attributes"][0], dict)
            assert "relationship_id" in response.json()["relationships"][0]["attributes"][0]


def test_get_ancestors(test_app):
    response = client.get("/api/people/1/ancestors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    response = client.get("/api/people/1/ancestors?depth=1")
    assert response.status_code == 200


def test_get_descendants(test_app):
    response = client.get("/api/people/1/descendants")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    response = client.get("/api/people/1/descendants?depth=1")
    assert response.status_code == 200


def test_get_extended_family(test_app):
    response = client.get("/api/people/1/extended_family")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    response = client.get("/api/people/1/extended_family?depth=1")
    assert response.status_code == 200


def test_get_related(test_app):
    response = client.get("/api/people/1/related")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    response = client.get("/api/people/1/related?depth=1")
    assert response.status_code == 200

def test_get_partial_tree(test_app):
    # Test with no depth specified
    response = client.get("/api/people/1/partial_tree")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Test with depth=1
    response = client.get("/api/people/1/partial_tree?depth=1")
    assert response.status_code == 200

    # Test with only_ancestors=true
    response = client.get("/api/people/1/partial_tree?only_ancestors=true")
    assert response.status_code == 200
    # Test with only_descendants=true
    response = client.get("/api/people/1/partial_tree?only_descendants=true")
    assert response.status_code == 200

def test_get_branch(test_app):
    # Test with no depth specified
    response = client.get("/api/people/1/branch")
    assert response.status_code == 200
    # Test with depth=1
    response = client.get("/api/people/1/branch?depth=1")
    assert response.status_code == 200


def test_search_people(test_app):
    # Test with no parameters
    response = client.get("/api/people/search")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Test with name parameter
    response = client.get("/api/people/search?name=John")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    for person in response.json():
        assert "John" in person["first_name"] or "John" in person["last_name"]

    # Test with gender parameter
    response = client.get("/api/people/search?gender=M")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    for person in response.json():
        assert person["gender"] == "M"

    # Test with place_of_birth
    response = client.get("/api/people/search?place_of_birth=London")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Test with attribute_key and attribute_value
    response = client.get("/api/people/search?attribute_key=occupation&attribute_value=teacher")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Test with multiple parameters
    response = client.get("/api/people/search?name=John&gender=M")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_all_sources_with_pagination(test_app):
    # Test with page=1 and page_size=2
    response = client.get("/api/sources?page=1&page_size=2")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "results" in response.json()
    assert "total_items" in response.json()
    assert "page" in response.json()
    assert "page_size" in response.json()
    assert "total_pages" in response.json()
    assert len(response.json()["results"]) == 2


    
