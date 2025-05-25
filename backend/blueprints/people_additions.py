# backend/blueprints/people.py additions
# Add this endpoint to the existing file

@people_bp.route('/global-people', methods=['GET'])
@require_auth
def get_global_people_not_in_tree_endpoint():
    """Fetch global people not in a specific tree."""
    db = g.db
    not_in_tree_id_str = request.args.get('not_in_tree')
    if not not_in_tree_id_str:
        abort(400, description="Missing required 'not_in_tree' parameter.")
    
    try:
        not_in_tree_id = uuid.UUID(not_in_tree_id_str)
    except ValueError:
        abort(400, description="Invalid tree ID format.")
    
    # Check if user has access to the specified tree
    tree = db.query(Tree).filter(Tree.id == not_in_tree_id).one_or_none()
    if not tree:
        abort(404, description=f"Tree with ID {not_in_tree_id_str} not found.")
    
    current_user_id = uuid.UUID(session['user_id'])
    has_tree_access = False
    
    # User has access if:
    # 1. They are the tree owner
    # 2. The tree is public (for viewing)
    # 3. They have an entry in TreeAccess
    if tree.created_by == current_user_id or tree.privacy_setting == TreePrivacySettingEnum.PUBLIC:
        has_tree_access = True
    else:
        tree_access = db.query(TreeAccess).filter(
            TreeAccess.tree_id == not_in_tree_id,
            TreeAccess.user_id == current_user_id
        ).one_or_none()
        if tree_access:
            has_tree_access = True
    
    if not has_tree_access:
        abort(403, description="You don't have access to this tree.")
    
    # Get pagination parameters and filters
    page, per_page, sort_by, sort_order = get_pagination_params()
    filters = {}
    
    # Process query parameters for filtering
    if 'search_term' in request.args:
        filters['search_term'] = request.args.get('search_term')
    if 'gender' in request.args:
        filters['gender'] = request.args.get('gender')
    if 'is_living' in request.args:
        is_living_str = request.args.get('is_living').lower()
        if is_living_str in ('true', '1', 'yes'):
            filters['is_living'] = True
        elif is_living_str in ('false', '0', 'no'):
            filters['is_living'] = False
    
    logger.info("Get global people not in tree", not_in_tree_id=not_in_tree_id, 
                user_id=current_user_id, filters=filters)
    
    try:
        result = get_global_people_not_in_tree_db(
            db, not_in_tree_id, page, per_page, sort_by, sort_order, filters
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error("Error fetching global people not in tree", exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error fetching global people.")
        raise
