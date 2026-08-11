def validate_metadata(metadata):
    """验证元数据"""
    required_fields = ["document_name", "publisher"]
    for field in required_fields:
        if field not in metadata or not metadata[field]:
            return False, f"缺少必要字段: {field}"
    return True, ""

def validate_conflict(conflict):
    """验证冲突数据"""
    required = ["conflict_id", "clause_a", "clause_b", "conflict_type"]
    for field in required:
        if field not in conflict:
            return False, f"冲突数据缺少字段: {field}"
    return True, ""