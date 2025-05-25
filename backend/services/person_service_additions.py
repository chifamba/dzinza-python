# backend/services/person_service.py additions
# Add this function to the existing file

def get_global_people_not_in_tree_db(db: DBSession, 
                                     tree_id: uuid.UUID, 
                                     page: int = -1,
                                     per_page: int = -1,
                                     sort_by: Optional[str] = "last_name",
                                     sort_order: Optional[str] = "asc",
                                     filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Fetches a paginated list of global people NOT associated with the given tree.
    Useful for adding existing people to a tree.
    """
    current_page = page if page != -1 else config.PAGINATION_DEFAULTS["page"]
    current_per_page = per_page if per_page != -1 else config.PAGINATION_DEFAULTS["per_page"]

    logger.info("Fetching global people not in tree", tree_id=tree_id, page=current_page, 
                per_page=current_per_page, sort_by=sort_by, filters=filters)
    try:
        # Create a subquery for person_ids already in the tree
        person_ids_in_tree = db.query(PersonTreeAssociation.person_id).filter(
            PersonTreeAssociation.tree_id == tree_id
        ).subquery('person_ids_in_tree')
        
        # Query Person objects NOT in the subquery
        query = db.query(Person).filter(~Person.id.in_(person_ids_in_tree))
        
        filter_conditions = [] 

        if filters:
            # Apply the same filters as get_all_people_db
            if 'is_living' in filters and isinstance(filters['is_living'], bool):
                filter_conditions.append(Person.is_living == filters['is_living'])
            if 'gender' in filters and filters['gender']: 
                filter_conditions.append(Person.gender.ilike(f"%{filters['gender']}%"))
            if 'search_term' in filters and filters['search_term']:
                term = f"%{filters['search_term']}%"
                search_conditions = [
                    Person.first_name.ilike(term), 
                    Person.last_name.ilike(term),
                    Person.nickname.ilike(term), 
                    Person.maiden_name.ilike(term)
                ]
                filter_conditions.append(or_(*search_conditions))

            # Apply date range filters
            date_filter_fields = {
                'birth_date_range_start': (Person.birth_date, '>='),
                'birth_date_range_end': (Person.birth_date, '<='),
                'death_date_range_start': (Person.death_date, '>='),
                'death_date_range_end': (Person.death_date, '<=')
            }
            for filter_key, (model_field, operator) in date_filter_fields.items():
                if filters.get(filter_key):
                    try:
                        parsed_date = date.fromisoformat(filters[filter_key])
                        if operator == '>=':
                            filter_conditions.append(model_field >= parsed_date)
                        elif operator == '<=':
                            filter_conditions.append(model_field <= parsed_date)
                    except ValueError:
                        logger.warning(f"Invalid date format for {filter_key}: {filters[filter_key]}.", exc_info=True)
                        abort(400, description={"message": "Validation failed", "details": {filter_key: f"Invalid date format: {filters[filter_key]}. Use YYYY-MM-DD."}})
            
            # Apply custom fields filter
            if filters.get('custom_fields_key') and 'custom_fields_value' in filters:
                key = filters['custom_fields_key']
                value = filters['custom_fields_value']
                filter_conditions.append(Person.custom_fields[key].astext == value)
        
        if filter_conditions:
            query = query.filter(*filter_conditions) 

        # Validate and apply sort
        if not (sort_by and hasattr(Person, sort_by)):
            logger.warning(f"Invalid or missing sort_by column '{sort_by}' for Person. Defaulting to 'last_name'.")
            sort_by = "last_name"
        
        if sort_order not in ['asc', 'desc']:
            sort_order = 'asc'
            
        paginated_result = paginate_query(
            query, Person, current_page, current_per_page, 
            config.PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order
        )
        
        logger.info(f"Found {paginated_result['total_items']} global people not in tree {tree_id}")
        return paginated_result
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, f"fetching global people not in tree {tree_id}", db)
    except Exception as e:
        logger.error("Unexpected error fetching global people not in tree.", tree_id=tree_id, exc_info=True)
        abort(500, "Error fetching global people not in tree.")
    return {}
