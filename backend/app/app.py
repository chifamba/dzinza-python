@app.get("/api/person_attributes")
def get_all_person_attributes_api(
    page: int = 1,
    page_size: int = 10,
    order_by: str = "id",
    order_direction: str = "asc",
    key: Optional[str] = None,
    value: Optional[str] = None,
    fields: Optional[str] = None
):
    fields_list = fields.split(",") if fields else None
    result = get_all_person_attributes(
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_direction=order_direction,
        key=key,
        value=value,
        fields=fields_list
    )
    return result


@app.get("/api/person_attributes/{person_attribute_id}")
def get_person_attribute_api(
    person_attribute_id: int, 
    fields: Optional[str] = None,
    include_person: bool = False
):
    fields_list = fields.split(",") if fields else None
    result = get_person_attribute(
        person_attribute_id=person_attribute_id, 
        fields=fields_list, 
        include_person=include_person
    )
    return result