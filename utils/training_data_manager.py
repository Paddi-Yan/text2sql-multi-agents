"""
Training data manager for handling CRUD operations and data management.
"""

import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

from .training_models import TrainingData, TrainingDataType, TrainingDataStats


class TrainingDataManager:
    """训练数据管理器"""
    
    def __init__(self):
        self.data_store: Dict[str, TrainingData] = {}
        self.stats = TrainingDataStats()
    
    def generate_id(self, content: str, data_type: TrainingDataType) -> str:
        """生成训练数据ID"""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{data_type.value}_{content_hash[:8]}_{uuid.uuid4().hex[:8]}"
    
    def add_training_data(self, training_data: TrainingData) -> bool:
        """添加训练数据"""
        try:
            if training_data.id in self.data_store:
                return False  # 数据已存在
            
            self.data_store[training_data.id] = training_data
            self.stats.update_stats(training_data)
            return True
        except Exception as e:
            print(f"Error adding training data: {e}")
            return False
    
    def get_training_data(self, data_id: str) -> Optional[TrainingData]:
        """获取训练数据"""
        return self.data_store.get(data_id)
    
    def update_training_data(self, data_id: str, updates: Dict[str, Any]) -> bool:
        """更新训练数据"""
        if data_id not in self.data_store:
            return False
        
        try:
            training_data = self.data_store[data_id]
            
            # 更新允许的字段
            if "content" in updates:
                training_data.content = updates["content"]
            if "metadata" in updates:
                training_data.metadata.update(updates["metadata"])
            if "question" in updates:
                training_data.question = updates["question"]
            if "sql" in updates:
                training_data.sql = updates["sql"]
            if "table_names" in updates:
                training_data.table_names = updates["table_names"]
            if "tags" in updates:
                training_data.tags = updates["tags"]
            if "embedding" in updates:
                training_data.embedding = updates["embedding"]
            
            return True
        except Exception as e:
            print(f"Error updating training data: {e}")
            return False
    
    def delete_training_data(self, data_id: str) -> bool:
        """删除训练数据"""
        if data_id in self.data_store:
            del self.data_store[data_id]
            # 重新计算统计信息
            self._recalculate_stats()
            return True
        return False
    
    def get_by_type(self, data_type: TrainingDataType, db_id: Optional[str] = None) -> List[TrainingData]:
        """按类型获取训练数据"""
        results = []
        for training_data in self.data_store.values():
            if training_data.data_type == data_type:
                if db_id is None or training_data.db_id == db_id:
                    results.append(training_data)
        return results
    
    def get_by_db_id(self, db_id: str) -> List[TrainingData]:
        """按数据库ID获取训练数据"""
        results = []
        for training_data in self.data_store.values():
            if training_data.db_id == db_id:
                results.append(training_data)
        return results
    
    def get_by_tags(self, tags: List[str], match_all: bool = False) -> List[TrainingData]:
        """按标签获取训练数据"""
        results = []
        for training_data in self.data_store.values():
            if match_all:
                # 必须包含所有标签
                if all(tag in training_data.tags for tag in tags):
                    results.append(training_data)
            else:
                # 包含任意一个标签即可
                if any(tag in training_data.tags for tag in tags):
                    results.append(training_data)
        return results
    
    def search_by_content(self, query: str, data_type: Optional[TrainingDataType] = None) -> List[TrainingData]:
        """按内容搜索训练数据"""
        results = []
        query_lower = query.lower()
        
        for training_data in self.data_store.values():
            if data_type and training_data.data_type != data_type:
                continue
            
            # 在内容、问题、SQL中搜索
            if (query_lower in training_data.content.lower() or
                (training_data.question and query_lower in training_data.question.lower()) or
                (training_data.sql and query_lower in training_data.sql.lower())):
                results.append(training_data)
        
        return results
    
    def get_stats(self) -> TrainingDataStats:
        """获取统计信息"""
        return self.stats
    
    def export_data(self, file_path: str) -> bool:
        """导出训练数据到文件"""
        try:
            export_data = {
                "data": [data.to_dict() for data in self.data_store.values()],
                "stats": {
                    "total_count": self.stats.total_count,
                    "ddl_count": self.stats.ddl_count,
                    "doc_count": self.stats.doc_count,
                    "sql_count": self.stats.sql_count,
                    "qa_pair_count": self.stats.qa_pair_count,
                    "domain_count": self.stats.domain_count,
                    "db_coverage": self.stats.db_coverage,
                    "tag_distribution": self.stats.tag_distribution
                },
                "exported_at": datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Error exporting data: {e}")
            return False
    
    def import_data(self, file_path: str) -> bool:
        """从文件导入训练数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            for data_dict in import_data.get("data", []):
                training_data = TrainingData.from_dict(data_dict)
                self.add_training_data(training_data)
            
            return True
        except Exception as e:
            print(f"Error importing data: {e}")
            return False
    
    def _recalculate_stats(self):
        """重新计算统计信息"""
        self.stats = TrainingDataStats()
        for training_data in self.data_store.values():
            self.stats.update_stats(training_data)
    
    def clear_all(self):
        """清空所有数据"""
        self.data_store.clear()
        self.stats = TrainingDataStats()
    
    def get_all_data(self) -> List[TrainingData]:
        """获取所有训练数据"""
        return list(self.data_store.values())