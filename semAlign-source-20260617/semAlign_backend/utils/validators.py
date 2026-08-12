import re
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from models.standard import Standard
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """数据验证器"""
    
    def __init__(self, db: Session):
        """函数内部辅助：init  。"""
        self.db = db
        self.rule_engine = None
    
    def set_rule_engine(self, rule_engine):
        """设置规则引擎（可选）"""
        self.rule_engine = rule_engine
    
    def validate_standard_no(self, standard_no: str) -> bool:
        """
        验证标准编号格式
        支持多种标准格式
        """
        if not standard_no or not isinstance(standard_no, str):
            return False
        
        # 常见标准编号格式
        patterns = [
            r'^[A-Z]+/[A-Z]?\s?\d+(\.\d+)*-\d{4}$',  # GB/T 2023.4.1-2021
            r'^[A-Z]+\s?\d+(\.\d+)*-\d{4}$',         # MH/T 3012.5-2020
            r'^ISO\s?\d+:\d{4}$',                     # ISO 9001:2015
            r'^[A-Z]+\s?\d+-\d{4}$',                  # GB 12345-2020
            r'^\d+\.\d+\.\d+-\d{4}$',                 # 纯数字格式
        ]
        
        for pattern in patterns:
            if re.match(pattern, standard_no):
                return True
        
        # 宽松模式：只要包含数字和字母，长度合适
        if 3 <= len(standard_no) <= 50 and re.search(r'[A-Z0-9]', standard_no):
            logger.warning(f"标准编号格式非标准: {standard_no}")
            return True
        
        return False
    
    def check_duplicate(self, standard_no: str) -> bool:
        """检查数据库中是否存在重复的标准编号"""
        try:
            existing = self.db.query(Standard).filter(
                Standard.standard_no == standard_no,
                Standard.is_active == True
            ).first()
            return existing is not None
        except Exception as e:
            logger.error(f"检查重复失败: {e}")
            return False
    
    def check_version_update(self, standard_no: str, version: str) -> bool:
        """检查是否需要更新版本"""
        try:
            existing = self.db.query(Standard).filter(
                Standard.standard_no == standard_no,
                Standard.is_active == True
            ).first()
            
            if existing and existing.version != version:
                return True
            return False
        except Exception as e:
            logger.error(f"检查版本更新失败: {e}")
            return False
    
    def _mark_invalid_record(self, record_copy: Dict, error: str) -> Dict:
        """函数内部辅助：mark invalid record。"""
        record_copy["validation_error"] = error
        record_copy["validation_status"] = "invalid"
        record_copy["status"] = "格式错误"
        return record_copy

    def _apply_duplicate_status(self, record_copy: Dict, result: Dict) -> None:
        """函数内部辅助：apply duplicate status。"""
        if self.check_version_update(record_copy["standard_no"], record_copy["version"]):
            record_copy["status"] = "版本待更新"
            record_copy["validation_status"] = "update"
            result["need_update"] += 1
            return
        record_copy["status"] = "重复数据"
        record_copy["validation_status"] = "duplicate"
        result["duplicate_rows"] += 1

    def _apply_rule_engine(self, record_copy: Dict) -> None:
        """函数内部辅助：apply rule engine。"""
        if not self.rule_engine:
            return
        try:
            violations = self.rule_engine.evaluate_rules(record_copy)
            if violations:
                record_copy["rule_violations"] = str(violations)
        except Exception as e:
            logger.error(f"规则验证失败: {e}")

    def _validate_single_record(self, record: Dict, result: Dict) -> Dict:
        """函数内部辅助：validate single record。"""
        record_copy = record.copy()

        if not self.validate_standard_no(record_copy["standard_no"]):
            return self._mark_invalid_record(record_copy, "标准编号格式错误")

        if self.check_duplicate(record_copy["standard_no"]):
            self._apply_duplicate_status(record_copy, result)
        else:
            record_copy["status"] = "有效"
            record_copy["validation_status"] = "valid"
            result["valid_rows"] += 1

        self._apply_rule_engine(record_copy)
        return record_copy

    def validate_records(self, records: List[Dict]) -> Dict:
        """批量验证记录"""
        result = {
            'total_rows': len(records),
            'valid_rows': 0,
            'need_update': 0,
            'duplicate_rows': 0,
            'data': []
        }

        for record in records:
            record_copy = self._validate_single_record(record, result)
            result['data'].append(record_copy)

        logger.info(f"验证完成: 总数={result['total_rows']}, 有效={result['valid_rows']}, 需更新={result['need_update']}, 重复={result['duplicate_rows']}")
        return result


def create_validator(db: Session) -> DataValidator:
    """构造与给定数据库会话绑定的校验器（供导入路由等使用）。"""
    return DataValidator(db)