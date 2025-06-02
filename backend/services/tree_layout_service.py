from sqlalchemy.orm import Session
from backend.models import TreeLayout
from backend.database import get_db_session # Assuming get_db_session gives a session
import structlog

logger = structlog.get_logger(__name__)

class TreeLayoutService:
    def __init__(self, db_session: Session = None):
        self.db = db_session if db_session else get_db_session()

    def create_or_update_layout(self, user_id: str, tree_id: str, layout_data: dict) -> TreeLayout | None:
        """
        Creates a new tree layout or updates an existing one for a specific user and tree.
        Ensures that a user can only create/update their own layout.
        """
        if not user_id or not tree_id:
            logger.error("create_or_update_layout: user_id and tree_id are required.")
            return None

        try:
            layout = self.db.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first()

            if layout:
                # Update existing layout
                layout.layout_data = layout_data
                logger.info("Updating existing layout", user_id=user_id, tree_id=tree_id)
            else:
                # Create new layout
                layout = TreeLayout(
                    user_id=user_id,
                    tree_id=tree_id,
                    layout_data=layout_data
                )
                self.db.add(layout)
                logger.info("Creating new layout", user_id=user_id, tree_id=tree_id)

            self.db.commit()
            self.db.refresh(layout) # Refresh to get DB defaults like id, created_at
            return layout
        except Exception as e:
            self.db.rollback()
            logger.error("Error in create_or_update_layout", error=str(e), user_id=user_id, tree_id=tree_id, exc_info=True)
            return None

    def get_layout(self, user_id: str, tree_id: str) -> TreeLayout | None:
        """
        Retrieves a specific tree layout for a user and tree.
        Ensures that a user can only access their own layout.
        """
        if not user_id or not tree_id:
            logger.error("get_layout: user_id and tree_id are required.")
            return None
        try:
            layout = self.db.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first()
            if not layout:
                logger.info("Layout not found", user_id=user_id, tree_id=tree_id)
                return None
            return layout
        except Exception as e:
            logger.error("Error in get_layout", error=str(e), user_id=user_id, tree_id=tree_id, exc_info=True)
            return None

    def delete_layout(self, user_id: str, tree_id: str) -> bool:
        """
        Deletes a specific tree layout for a user and tree.
        Ensures that a user can only delete their own layout.
        Returns True if deletion was successful, False otherwise.
        """
        if not user_id or not tree_id:
            logger.error("delete_layout: user_id and tree_id are required.")
            return False
        try:
            layout = self.db.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first()
            if layout:
                self.db.delete(layout)
                self.db.commit()
                logger.info("Layout deleted successfully", user_id=user_id, tree_id=tree_id)
                return True
            else:
                logger.info("Layout not found for deletion", user_id=user_id, tree_id=tree_id)
                return False
        except Exception as e:
            self.db.rollback()
            logger.error("Error in delete_layout", error=str(e), user_id=user_id, tree_id=tree_id, exc_info=True)
            return False

# Example of how to get a session if needed, or pass it directly
# def get_tree_layout_service(db_session: Session = None) -> TreeLayoutService:
#     if db_session is None:
#         db_session = get_db_session() # This function needs to be available from your db setup
#     return TreeLayoutService(db_session)
