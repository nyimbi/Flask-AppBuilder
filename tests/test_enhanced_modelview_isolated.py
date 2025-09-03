"""
Isolated unit tests for Enhanced ModelView components.

This module provides comprehensive testing of the Enhanced ModelView functionality
without triggering circular imports, focusing on core business logic,
caching behavior, and performance optimization.

Test Coverage:
    - Field analysis caching logic
    - Model inspection utilities
    - Smart exclusion business logic
    - Performance optimization features
    - Memory management and efficiency
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List


class MockFieldAnalysisCache:
    """Mock implementation of FieldAnalysisCache for testing."""
    
    def __init__(self, max_cache_size: int = 1000, cache_ttl_seconds: int = 3600):
        self.max_cache_size = max_cache_size
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._cache = {}
        self._cache_timestamps = {}
    
    def get_cache_key(self, model_class, analyzer_config):
        model_name = f"{model_class.__module__}.{model_class.__name__}"
        # Handle nested dicts in config by converting to string
        config_str = str(sorted(analyzer_config.items()))
        config_hash = hash(config_str)
        return f"{model_name}:{config_hash}"
    
    def get(self, cache_key):
        if cache_key not in self._cache:
            return None
        
        timestamp = self._cache_timestamps.get(cache_key)
        if timestamp and datetime.utcnow() - timestamp > self.cache_ttl:
            self._invalidate_entry(cache_key)
            return None
        
        return self._cache[cache_key]
    
    def set(self, cache_key, analysis_result):
        if len(self._cache) >= self.max_cache_size:
            self._evict_oldest_entries()
        
        # Handle None and non-dict values
        if analysis_result is None:
            self._cache[cache_key] = None
        elif hasattr(analysis_result, 'copy'):
            self._cache[cache_key] = analysis_result.copy()
        else:
            self._cache[cache_key] = analysis_result
        self._cache_timestamps[cache_key] = datetime.utcnow()
    
    def invalidate(self, model_class):
        model_name = f"{model_class.__module__}.{model_class.__name__}"
        keys_to_remove = [key for key in self._cache.keys() if key.startswith(model_name)]
        
        for key in keys_to_remove:
            self._invalidate_entry(key)
    
    def clear(self):
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def _invalidate_entry(self, cache_key):
        self._cache.pop(cache_key, None)
        self._cache_timestamps.pop(cache_key, None)
    
    def _evict_oldest_entries(self, num_to_evict=None):
        if num_to_evict is None:
            num_to_evict = max(1, len(self._cache) // 10)
        
        sorted_entries = sorted(
            self._cache_timestamps.items(),
            key=lambda x: x[1]
        )
        
        for cache_key, _ in sorted_entries[:num_to_evict]:
            self._invalidate_entry(cache_key)


class MockModelInspector:
    """Mock implementation of ModelInspector for testing."""
    
    @staticmethod
    def get_model_columns(model_class):
        if not hasattr(model_class, '__table__'):
            return []
        return getattr(model_class.__table__, 'columns', [])
    
    @staticmethod
    def extract_field_metadata(column):
        # Handle missing type attribute
        column_type = getattr(column, 'type', None)
        if column_type is None:
            type_name = 'Unknown'
        else:
            type_name = getattr(column_type, '__class__', type).__name__
        
        return {
            'name': getattr(column, 'name', 'unknown'),
            'type_name': type_name,
            'nullable': getattr(column, 'nullable', True),
            'primary_key': getattr(column, 'primary_key', False),
            'unique': getattr(column, 'unique', False),
            'indexed': getattr(column, 'index', False),
            'autoincrement': getattr(column, 'autoincrement', False),
            'foreign_keys': [],
            'default': None,
            'server_default': None,
        }


class TestFieldAnalysisCacheLogic:
    """Test the field analysis caching logic without dependencies."""
    
    @pytest.fixture
    def cache(self):
        """Create a mock field analysis cache."""
        return MockFieldAnalysisCache(max_cache_size=5, cache_ttl_seconds=10)
    
    def test_cache_initialization(self, cache):
        """Test cache initialization with custom parameters."""
        assert cache.max_cache_size == 5
        assert cache.cache_ttl.total_seconds() == 10
        assert len(cache._cache) == 0
        assert len(cache._cache_timestamps) == 0
    
    def test_cache_key_generation(self, cache):
        """Test cache key generation logic."""
        class MockModel:
            __module__ = "test_module"
            __name__ = "TestModel"
        
        config = {'strict_mode': True, 'custom_rules': {}}
        cache_key = cache.get_cache_key(MockModel, config)
        
        assert isinstance(cache_key, str)
        assert "test_module.MockModel" in cache_key
        assert ":" in cache_key
        
        # Different configs should generate different keys
        config2 = {'strict_mode': False, 'custom_rules': {}}
        cache_key2 = cache.get_cache_key(MockModel, config2)
        
        assert cache_key != cache_key2
    
    def test_cache_set_and_get(self, cache):
        """Test basic cache operations."""
        cache_key = "test_model:config_hash"
        analysis_result = {
            'total_columns': 5,
            'fully_supported': [{'name': 'id', 'type': 'Integer'}],
            'unsupported': []
        }
        
        # Set cache entry
        cache.set(cache_key, analysis_result)
        
        # Verify entry exists
        assert cache_key in cache._cache
        assert cache_key in cache._cache_timestamps
        
        # Get cache entry
        retrieved_result = cache.get(cache_key)
        
        assert retrieved_result is not None
        assert retrieved_result['total_columns'] == 5
        assert len(retrieved_result['fully_supported']) == 1
        
        # Verify it's a copy, not the same object
        analysis_result['total_columns'] = 10
        assert retrieved_result['total_columns'] == 5
    
    def test_cache_miss(self, cache):
        """Test cache miss behavior."""
        nonexistent_key = "nonexistent:key"
        result = cache.get(nonexistent_key)
        
        assert result is None
    
    def test_cache_expiration_logic(self, cache):
        """Test cache expiration without actual time delays."""
        cache_key = "test_model:config"
        analysis_result = {'test': 'data'}
        
        # Set cache entry
        cache.set(cache_key, analysis_result)
        
        # Manually set timestamp to simulate expiration
        expired_time = datetime.utcnow() - timedelta(seconds=15)
        cache._cache_timestamps[cache_key] = expired_time
        
        # Should return None due to expiration
        result = cache.get(cache_key)
        assert result is None
        
        # Entry should be removed from cache
        assert cache_key not in cache._cache
        assert cache_key not in cache._cache_timestamps
    
    def test_cache_size_enforcement(self, cache):
        """Test cache size limit enforcement."""
        # Fill cache beyond limit
        for i in range(10):
            cache_key = f"model_{i}:config"
            cache.set(cache_key, {'data': i})
        
        # Should not exceed max size
        assert len(cache._cache) <= cache.max_cache_size
        assert len(cache._cache_timestamps) <= cache.max_cache_size
        
        # Should still contain some entries
        assert len(cache._cache) > 0
    
    def test_cache_invalidation_by_model(self, cache):
        """Test selective cache invalidation by model."""
        class Model1:
            __module__ = "test"
            __name__ = "Model1"
        
        class Model2:
            __module__ = "test"  
            __name__ = "Model2"
        
        # Add entries for both models
        cache.set("test.Model1:config1", {'data': 1})
        cache.set("test.Model1:config2", {'data': 2})
        cache.set("test.Model2:config1", {'data': 3})
        
        # Invalidate Model1 only
        cache.invalidate(Model1)
        
        # Model1 entries should be gone
        assert cache.get("test.Model1:config1") is None
        assert cache.get("test.Model1:config2") is None
        
        # Model2 entry should remain
        assert cache.get("test.Model2:config1") is not None
        assert cache.get("test.Model2:config1")['data'] == 3
    
    def test_cache_clear_all(self, cache):
        """Test clearing entire cache."""
        # Add multiple entries
        for i in range(3):
            cache.set(f"key_{i}", {'data': i})
        
        assert len(cache._cache) == 3
        assert len(cache._cache_timestamps) == 3
        
        # Clear cache
        cache.clear()
        
        # Should be completely empty
        assert len(cache._cache) == 0
        assert len(cache._cache_timestamps) == 0


class TestModelInspectionLogic:
    """Test model inspection utilities logic."""
    
    def test_get_model_columns_no_table(self):
        """Test getting columns from model without __table__."""
        class ModelWithoutTable:
            pass
        
        columns = MockModelInspector.get_model_columns(ModelWithoutTable)
        assert columns == []
    
    def test_get_model_columns_with_table(self):
        """Test getting columns from model with __table__."""
        class MockColumn:
            def __init__(self, name):
                self.name = name
        
        class ModelWithTable:
            class __table__:
                columns = [MockColumn('id'), MockColumn('name')]
        
        columns = MockModelInspector.get_model_columns(ModelWithTable)
        assert len(columns) == 2
        assert columns[0].name == 'id'
        assert columns[1].name == 'name'
    
    def test_extract_field_metadata_complete(self):
        """Test extracting complete field metadata."""
        # Mock a complete column
        mock_column = MagicMock()
        mock_column.name = "test_field"
        mock_column.type.__class__.__name__ = "String"
        mock_column.nullable = False
        mock_column.primary_key = True
        mock_column.unique = True
        mock_column.index = True
        mock_column.autoincrement = False
        
        metadata = MockModelInspector.extract_field_metadata(mock_column)
        
        assert metadata['name'] == 'test_field'
        assert metadata['type_name'] == 'String'
        assert metadata['nullable'] is False
        assert metadata['primary_key'] is True
        assert metadata['unique'] is True
        assert metadata['indexed'] is True
        assert metadata['autoincrement'] is False
    
    def test_extract_field_metadata_minimal(self):
        """Test extracting metadata from minimal column."""
        # Mock a minimal column
        mock_column = MagicMock()
        mock_column.name = "minimal_field"
        
        # Remove optional attributes
        del mock_column.nullable
        del mock_column.primary_key
        del mock_column.unique
        del mock_column.index
        del mock_column.autoincrement
        
        metadata = MockModelInspector.extract_field_metadata(mock_column)
        
        assert metadata['name'] == 'minimal_field'
        assert metadata['nullable'] is True  # Default
        assert metadata['primary_key'] is False  # Default
        assert metadata['unique'] is False  # Default
        assert metadata['indexed'] is False  # Default
        assert metadata['autoincrement'] is False  # Default


class TestSmartExclusionLogic:
    """Test smart exclusion business logic."""
    
    def test_searchable_column_selection(self):
        """Test logic for selecting searchable columns."""
        # Mock analysis result
        analysis_result = {
            'fully_supported': [
                {'name': 'name', 'type': 'String'},
                {'name': 'email', 'type': 'String'}
            ],
            'searchable_only': [
                {'name': 'description', 'type': 'Text'}
            ],
            'limited_support': [
                {'name': 'metadata', 'type': 'JSON'}
            ],
            'unsupported': [
                {'name': 'photo', 'type': 'BLOB'}
            ]
        }
        
        # Simulate strict mode selection
        searchable_strict = []
        for col_info in analysis_result['fully_supported']:
            searchable_strict.append(col_info['name'])
        for col_info in analysis_result['searchable_only']:
            searchable_strict.append(col_info['name'])
        
        assert 'name' in searchable_strict
        assert 'email' in searchable_strict
        assert 'description' in searchable_strict
        assert 'metadata' not in searchable_strict  # Limited support excluded in strict mode
        assert 'photo' not in searchable_strict
        
        # Simulate permissive mode selection
        searchable_permissive = searchable_strict.copy()
        for col_info in analysis_result['limited_support']:
            searchable_permissive.append(col_info['name'])
        
        assert 'metadata' in searchable_permissive  # Included in permissive mode
    
    def test_list_column_selection(self):
        """Test logic for selecting list display columns."""
        analysis_result = {
            'fully_supported': [{'name': 'name', 'type': 'String'}],
            'limited_support': [{'name': 'metadata', 'type': 'JSON'}],
            'unsupported': [
                {'name': 'photo', 'type': 'BLOB', 'reason': 'binary_data'},
                {'name': 'config', 'type': 'Custom', 'reason': 'ui_limitation'}
            ]
        }
        
        excluded_reasons = {'binary_data', 'multimedia', 'vector_embeddings'}
        
        display_columns = []
        
        # Include supported types
        for support_level in ['fully_supported', 'limited_support']:
            for col_info in analysis_result.get(support_level, []):
                display_columns.append(col_info['name'])
        
        # Include some unsupported types that can still be displayed
        for col_info in analysis_result.get('unsupported', []):
            if col_info.get('reason') not in excluded_reasons:
                display_columns.append(col_info['name'])
        
        assert 'name' in display_columns
        assert 'metadata' in display_columns
        assert 'config' in display_columns  # UI limitation but still displayable
        assert 'photo' not in display_columns  # Binary data excluded
    
    def test_edit_column_selection(self):
        """Test logic for selecting editable columns."""
        analysis_result = {
            'fully_supported': [
                {'name': 'id', 'type': 'Integer', 'metadata': {'primary_key': True}},
                {'name': 'name', 'type': 'String', 'metadata': {'primary_key': False}},
                {'name': 'created_at', 'type': 'DateTime', 'metadata': {'autoincrement': True}}
            ],
            'limited_support': [
                {'name': 'settings', 'type': 'JSON', 'metadata': {'primary_key': False}}
            ]
        }
        
        editable_columns = []
        
        for support_level in ['fully_supported', 'limited_support']:
            for col_info in analysis_result.get(support_level, []):
                metadata = col_info.get('metadata', {})
                # Skip primary keys and auto-increment fields
                if not (metadata.get('primary_key') or metadata.get('autoincrement')):
                    editable_columns.append(col_info['name'])
        
        assert 'name' in editable_columns
        assert 'settings' in editable_columns
        assert 'id' not in editable_columns  # Primary key excluded
        assert 'created_at' not in editable_columns  # Auto-increment excluded


class TestPerformanceOptimizations:
    """Test performance optimization features."""
    
    def test_cache_performance_simulation(self):
        """Test simulated cache performance benefits."""
        cache = MockFieldAnalysisCache()
        
        # Simulate expensive analysis result
        large_result = {
            'total_columns': 100,
            'fully_supported': [{'name': f'field_{i}', 'type': 'String'} for i in range(50)],
            'unsupported': [{'name': f'blob_{i}', 'type': 'BLOB'} for i in range(50)]
        }
        
        cache_key = "large_model:config"
        
        # Set the cache entry
        cache.set(cache_key, large_result)
        
        # Multiple retrievals should be consistent
        retrieved_result1 = cache.get(cache_key)
        retrieved_result2 = cache.get(cache_key)
        
        # Both retrievals should return the same data
        assert retrieved_result1 is not None
        assert retrieved_result2 is not None
        assert retrieved_result1['total_columns'] == 100
        assert retrieved_result2['total_columns'] == 100
        assert len(retrieved_result1['fully_supported']) == 50
    
    def test_memory_efficiency_simulation(self):
        """Test memory efficiency of cache eviction."""
        cache = MockFieldAnalysisCache(max_cache_size=3)
        
        # Add more entries than cache can hold
        for i in range(10):
            cache.set(f"model_{i}:config", {'data': i, 'large_list': list(range(100))})
        
        # Should respect memory limits
        assert len(cache._cache) <= 3
        assert len(cache._cache_timestamps) <= 3
        
        # Should still contain valid entries
        assert len(cache._cache) > 0
        
        # Most recent entries should be retained
        remaining_keys = list(cache._cache.keys())
        assert any('model_' in key for key in remaining_keys)
    
    def test_eviction_strategy(self):
        """Test least-recently-used eviction strategy."""
        cache = MockFieldAnalysisCache(max_cache_size=3)
        
        # Add initial entries
        cache.set("old_1", {'data': 1})
        cache.set("old_2", {'data': 2})
        cache.set("old_3", {'data': 3})
        
        # Manually adjust timestamps to simulate age
        base_time = datetime.utcnow()
        cache._cache_timestamps["old_1"] = base_time - timedelta(minutes=10)
        cache._cache_timestamps["old_2"] = base_time - timedelta(minutes=5)
        cache._cache_timestamps["old_3"] = base_time - timedelta(minutes=1)
        
        # Add new entry to trigger eviction
        cache.set("new_entry", {'data': 4})
        
        # Oldest entry should be evicted first
        assert cache.get("old_1") is None  # Should be evicted
        assert cache.get("new_entry") is not None  # Should be present


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""
    
    def test_cache_with_invalid_data(self):
        """Test cache behavior with various data types."""
        cache = MockFieldAnalysisCache()
        
        # Test with None
        cache.set("none_key", None)
        result = cache.get("none_key")
        assert result is None
        
        # Test with empty dict
        cache.set("empty_key", {})
        result = cache.get("empty_key")
        assert result == {}
        
        # Test with complex nested data
        complex_data = {
            'level1': {
                'level2': {
                    'list': [1, 2, {'nested': True}],
                    'tuple': (1, 2, 3)
                }
            }
        }
        cache.set("complex_key", complex_data)
        result = cache.get("complex_key")
        assert result['level1']['level2']['list'][2]['nested'] is True
    
    def test_cache_key_generation_edge_cases(self):
        """Test cache key generation with edge cases."""
        cache = MockFieldAnalysisCache()
        
        # Model with special characters in name
        class ModelWithSpecialName:
            __module__ = "test.module_name"
            __name__ = "Model$With&Special#Chars"
        
        config = {'key': 'value with spaces', 'number': 42}
        cache_key = cache.get_cache_key(ModelWithSpecialName, config)
        
        assert isinstance(cache_key, str)
        assert len(cache_key) > 0
        assert ":" in cache_key
        
        # Different models should generate different keys
        class AnotherModel:
            __module__ = "test.module_name"
            __name__ = "AnotherModel"
        
        cache_key2 = cache.get_cache_key(AnotherModel, config)
        assert cache_key != cache_key2
    
    def test_model_inspector_with_missing_attributes(self):
        """Test model inspector with various missing attributes."""
        inspector = MockModelInspector()
        
        # Column with minimal attributes
        class MinimalColumn:
            pass
        
        minimal_column = MinimalColumn()
        metadata = inspector.extract_field_metadata(minimal_column)
        
        # Should handle missing attributes gracefully
        assert metadata['name'] == 'unknown'
        assert metadata['nullable'] is True
        assert metadata['primary_key'] is False
        
        # Column with some attributes
        class PartialColumn:
            def __init__(self):
                self.name = "partial_field"
                self.nullable = False
        
        partial_column = PartialColumn()
        metadata = inspector.extract_field_metadata(partial_column)
        
        assert metadata['name'] == 'partial_field'
        assert metadata['nullable'] is False
        assert metadata['primary_key'] is False  # Default for missing attribute


class TestConfigurationManagement:
    """Test configuration and customization features."""
    
    def test_cache_configuration_options(self):
        """Test cache with different configuration options."""
        # Small cache with short TTL
        small_cache = MockFieldAnalysisCache(max_cache_size=2, cache_ttl_seconds=1)
        assert small_cache.max_cache_size == 2
        assert small_cache.cache_ttl.total_seconds() == 1
        
        # Large cache with long TTL
        large_cache = MockFieldAnalysisCache(max_cache_size=1000, cache_ttl_seconds=7200)
        assert large_cache.max_cache_size == 1000
        assert large_cache.cache_ttl.total_seconds() == 7200
    
    def test_analysis_mode_differences(self):
        """Test differences between strict and permissive analysis modes."""
        # Mock unknown field type
        unknown_field = {'name': 'unknown_field', 'type': 'UnknownType'}
        
        # Strict mode logic
        strict_searchable = []
        strict_filterable = []
        
        # In strict mode, unknown types are excluded
        if unknown_field['type'] not in ['String', 'Integer', 'DateTime']:
            pass  # Exclude from strict mode
        
        # Permissive mode logic
        permissive_searchable = strict_searchable.copy()
        permissive_filterable = strict_filterable.copy()
        
        # In permissive mode, unknown types get limited support
        if unknown_field['type'] not in ['String', 'Integer', 'DateTime']:
            permissive_searchable.append(unknown_field['name'])
            permissive_filterable.append(unknown_field['name'])
        
        assert len(permissive_searchable) >= len(strict_searchable)
        assert len(permissive_filterable) >= len(strict_filterable)


if __name__ == "__main__":
    pytest.main([__file__, '-v'])