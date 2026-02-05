class CacheKeys:

    # ==================== PUBLIC REPOSITORY KEYS ====================

    @staticmethod
    def repo_detail_public(repo_id):
        return f"scm:repo_detail_public:{repo_id}"

    @staticmethod
    def repo_tags(repo_id):
        return f"scm:repo_tags:{repo_id}"

    # ==================== USER-SPECIFIC KEYS ====================

    @staticmethod
    def user_repo_list(user_id, search_query=""):
        return f"scm:user:{user_id}:repositories:{search_query}"

    @staticmethod
    def user_starred(user_id):
        return f"scm:user:{user_id}:starred"

    @staticmethod
    def user_stats(user_id):
        return f"scm:user:{user_id}:stats"

    # ==================== EXPLORE KEYS ====================

    @staticmethod
    def explore(query=None, badges=None):
        query_str = query if query else "None"
        badges_str = ":".join(sorted(badges)) if badges else ""
        return f"scm:explore:q:{query_str}:badges:{badges_str}"


    # ==================== INVALIDATION ====================

    @staticmethod
    def get_repo_invalidation_keys(repo_id):
        return [
            CacheKeys.repo_detail_public(repo_id),
            CacheKeys.repo_tags(repo_id),
        ]

    @staticmethod
    def get_user_invalidation_keys(user_id):
        return [
            CacheKeys.user_repo_list(user_id, ""),  # Base key
            CacheKeys.user_starred(user_id),
            CacheKeys.user_stats(user_id),
        ]

    @staticmethod
    def get_explore_invalidation_pattern():
        return "scm:*:explore:*"
