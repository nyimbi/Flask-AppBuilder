"""
Enhanced Database Inspector for Flask-AppBuilder Generation System

Provides comprehensive database introspection capabilities with advanced
relationship analysis, constraint detection, and metadata extraction.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from sqlalchemy import (
    create_engine,
    MetaData,
    inspect,
    Table,
    Column,
    ForeignKey,
    text,
    types
)
from sqlalchemy.engine import Engine
from sqlalchemy.engine.reflection import Inspector
import inflect

logger = logging.getLogger(__name__)
p = inflect.engine()


class RelationshipType(Enum):
    """Types of database relationships."""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"
    SELF_REFERENCING = "self_referencing"
    HIERARCHICAL = "hierarchical"


class ColumnType(Enum):
    """Enhanced column type categories."""
    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    UNIQUE = "unique"
    INDEX = "index"
    NULLABLE = "nullable"
    ENUM = "enum"
    JSON = "json"
    ARRAY = "array"
    BINARY = "binary"
    TEXT = "text"
    NUMERIC = "numeric"
    DATE_TIME = "date_time"
    BOOLEAN = "boolean"


@dataclass
class ColumnInfo:
    """Enhanced column information."""
    name: str
    type: str
    sql_type: type
    nullable: bool
    primary_key: bool
    foreign_key: bool
    unique: bool
    default: Any
    comment: Optional[str]
    length: Optional[int]
    precision: Optional[int]
    scale: Optional[int]
    enum_values: Optional[List[str]]
    is_identity: bool
    autoincrement: bool

    # Enhanced metadata
    category: ColumnType
    display_name: str
    description: str
    validation_rules: List[str]
    widget_type: str
    form_field_type: str


@dataclass
class RelationshipInfo:
    """Enhanced relationship information."""
    name: str
    type: RelationshipType
    local_table: str
    remote_table: str
    local_columns: List[str]
    remote_columns: List[str]
    association_table: Optional[str]
    back_populates: str
    cascade_options: List[str]
    lazy_loading: str

    # Enhanced metadata
    display_name: str
    description: str
    cardinality_description: str
    ui_hint: str

@dataclass
class MasterDetailInfo:
    """Information about master-detail relationship patterns."""
    parent_table: str
    child_table: str
    relationship: RelationshipInfo
    is_suitable_for_inline: bool
    expected_child_count: str  # "few", "moderate", "many"
    child_display_fields: List[str]
    parent_display_fields: List[str]
    inline_edit_suitable: bool
    supports_bulk_operations: bool
    
    # UI Configuration
    default_child_count: int
    min_child_forms: int
    max_child_forms: int
    enable_sorting: bool
    enable_deletion: bool
    child_form_layout: str  # "tabular", "stacked", "accordion"


@dataclass
class TableInfo:
    """Enhanced table information."""
    name: str
    schema: Optional[str]
    comment: Optional[str]
    columns: List[ColumnInfo]
    relationships: List[RelationshipInfo]
    indexes: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]]

    # Enhanced metadata
    display_name: str
    description: str
    category: str
    icon: str
    estimated_rows: int
    is_association_table: bool
    view_types: List[str]
    security_level: str


class EnhancedDatabaseInspector:
    """
    Enhanced database inspector with comprehensive introspection capabilities.

    Provides advanced database analysis including:
    - Detailed column metadata with validation rules
    - Sophisticated relationship analysis
    - Association table detection
    - Performance hints and recommendations
    - UI generation metadata
    """

    def __init__(self, database_uri: str):
        """
        Initialize the database inspector.

        Args:
            database_uri: Database connection string
        """
        self.database_uri = database_uri
        self._engine = None
        self._inspector = None
        self._metadata = None
        self._connection = None
        
        # Analysis caches
        self._table_stats: Dict[str, Dict[str, Any]] = {}
        self._relationship_cache: Dict[str, List[RelationshipInfo]] = {}
        self._association_tables: Set[str] = set()
        
        # Resource management flags
        self._is_connected = False
        self._auto_cleanup = True

        logger.info(f"Initialized database inspector for: {database_uri}")

    @property
    def engine(self):
        """Lazy-loaded database engine with proper connection management."""
        if self._engine is None:
            try:
                self._engine = create_engine(
                    self.database_uri,
                    pool_pre_ping=True,  # Verify connections before use
                    pool_recycle=3600,   # Recycle connections after 1 hour
                    connect_args={'connect_timeout': 30}  # 30 second connection timeout
                )
                logger.info(f"Created database engine for: {self._engine.url.database}")
            except Exception as e:
                logger.error(f"Failed to create database engine: {e}")
                raise
        return self._engine
    
    @property
    def inspector(self):
        """Lazy-loaded database inspector."""
        if self._inspector is None:
            self._inspector = inspect(self.engine)
            logger.debug("Created database inspector")
        return self._inspector
    
    @property
    def metadata(self):
        """Lazy-loaded database metadata with reflection."""
        if self._metadata is None:
            try:
                self._metadata = MetaData()
                with self.engine.connect() as conn:
                    self._metadata.reflect(bind=conn)
                logger.info(f"Reflected metadata for {len(self._metadata.tables)} tables")
            except Exception as e:
                logger.error(f"Failed to reflect database metadata: {e}")
                raise
        return self._metadata
    
    def connect(self):
        """Explicitly connect to the database."""
        if not self._is_connected:
            try:
                # Test connection by accessing properties
                _ = self.engine
                _ = self.inspector
                _ = self.metadata
                self._is_connected = True
                logger.info("Successfully connected to database")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                self.cleanup()
                raise
        return self
    
    def cleanup(self):
        """Clean up database connections and resources."""
        try:
            if self._connection and not self._connection.closed:
                self._connection.close()
                self._connection = None
                
            if self._engine:
                self._engine.dispose()
                self._engine = None
                
            self._inspector = None
            self._metadata = None
            self._is_connected = False
            
            logger.info("Cleaned up database connections")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry - connect to database."""
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup connections."""
        if self._auto_cleanup:
            self.cleanup()
        
        # Don't suppress exceptions
        return False
    
    def __del__(self):
        """Destructor - ensure cleanup happens."""
        try:
            if self._auto_cleanup:
                self.cleanup()
        except:
            # Ignore errors during destruction
            pass

    def analyze_database(self) -> Dict[str, Any]:
        """
        Perform comprehensive database analysis.

        Returns:
            Dictionary containing complete database analysis
        """
        logger.info("Starting comprehensive database analysis...")

        tables = self.get_all_tables()

        # Identify association tables first
        self._identify_association_tables()

        analysis = {
            'database_info': self._get_database_info(),
            'tables': {},
            'relationships': {},
            'association_tables': list(self._association_tables),
            'statistics': self._get_database_statistics(),
            'recommendations': self._generate_recommendations()
        }

        # Analyze each table
        for table_name in tables:
            if not table_name.startswith('ab_'):  # Skip Flask-AppBuilder system tables
                table_info = self.analyze_table(table_name)
                analysis['tables'][table_name] = table_info
                analysis['relationships'][table_name] = table_info.relationships

        logger.info(f"Analysis complete. Found {len(analysis['tables'])} tables")
        return analysis

    def analyze_table(self, table_name: str) -> TableInfo:
        """
        Analyze a single table comprehensively.

        Args:
            table_name: Name of the table to analyze

        Returns:
            Complete table analysis information
        """
        table = self.metadata.tables[table_name]

        # Basic table info
        table_comment = self.inspector.get_table_comment(table_name)

        # Analyze columns
        columns = []
        for column in table.columns:
            column_info = self._analyze_column(column, table_name)
            columns.append(column_info)

        # Analyze relationships
        relationships = self._analyze_relationships(table_name)

        # Get indexes and constraints
        indexes = self.inspector.get_indexes(table_name)
        constraints = self._get_table_constraints(table_name)

        # Determine table category and metadata
        category = self._categorize_table(table_name, columns)
        icon = self._get_table_icon(category, table_name)
        estimated_rows = self._estimate_table_rows(table_name)
        is_association = table_name in self._association_tables
        view_types = self._suggest_view_types(columns, relationships, is_association)
        security_level = self._assess_security_level(columns)

        return TableInfo(
            name=table_name,
            schema=table.schema,
            comment=table_comment.get('text') if table_comment else None,
            columns=columns,
            relationships=relationships,
            indexes=indexes,
            constraints=constraints,
            display_name=self._generate_display_name(table_name),
            description=self._generate_table_description(table_name, columns),
            category=category,
            icon=icon,
            estimated_rows=estimated_rows,
            is_association_table=is_association,
            view_types=view_types,
            security_level=security_level
        )

    def _analyze_column(self, column: Column, table_name: str) -> ColumnInfo:
        """Analyze a single column with enhanced metadata."""
        sql_type = column.type
        type_str = str(sql_type)

        # Get column comment
        column_data = next(
            (col for col in self.inspector.get_columns(table_name)
             if col['name'] == column.name),
            {}
        )
        comment = column_data.get('comment')

        # Determine column category
        category = self._categorize_column(column, table_name)

        # Extract type information
        length = getattr(sql_type, 'length', None)
        precision = getattr(sql_type, 'precision', None)
        scale = getattr(sql_type, 'scale', None)
        enum_values = getattr(sql_type, 'enums', None) if hasattr(sql_type, 'enums') else None

        # Generate metadata
        display_name = self._generate_column_display_name(column.name)
        description = self._generate_column_description(column, category, comment)
        validation_rules = self._generate_validation_rules(column, category)
        widget_type = self._suggest_widget_type(column, category)
        form_field_type = self._suggest_form_field_type(column, category)

        return ColumnInfo(
            name=column.name,
            type=type_str,
            sql_type=type(sql_type),
            nullable=column.nullable,
            primary_key=column.primary_key,
            foreign_key=bool(column.foreign_keys),
            unique=column.unique if hasattr(column, 'unique') else False,
            default=column.default,
            comment=comment,
            length=length,
            precision=precision,
            scale=scale,
            enum_values=enum_values,
            is_identity=getattr(column_data, 'identity', False),
            autoincrement=column.autoincrement,
            category=category,
            display_name=display_name,
            description=description,
            validation_rules=validation_rules,
            widget_type=widget_type,
            form_field_type=form_field_type
        )

    def _analyze_relationships(self, table_name: str) -> List[RelationshipInfo]:
        """Analyze relationships for a table."""
        if table_name in self._relationship_cache:
            return self._relationship_cache[table_name]

        relationships = []
        foreign_keys = self.inspector.get_foreign_keys(table_name)

        for fk in foreign_keys:
            rel_info = self._analyze_single_relationship(table_name, fk)
            if rel_info:
                relationships.append(rel_info)

        # Cache the results
        self._relationship_cache[table_name] = relationships
        return relationships

    def _analyze_single_relationship(self, table_name: str, fk: Dict[str, Any]) -> Optional[RelationshipInfo]:
        """Analyze a single foreign key relationship."""
        referred_table = fk['referred_table']
        constrained_columns = fk['constrained_columns']
        referred_columns = fk['referred_columns']

        # Determine relationship type
        rel_type = self._determine_relationship_type(table_name, fk)

        # Generate relationship name
        rel_name = self._generate_relationship_name(table_name, referred_table, constrained_columns, rel_type)
        back_populates = self._generate_back_populates_name(table_name, referred_table, rel_type)

        # Determine association table for many-to-many
        association_table = None
        if rel_type == RelationshipType.MANY_TO_MANY:
            association_table = self._find_association_table(table_name, referred_table)

        # Generate display metadata
        display_name = self._generate_relationship_display_name(rel_name, rel_type)
        description = self._generate_relationship_description(table_name, referred_table, rel_type)
        cardinality_desc = self._get_cardinality_description(rel_type)
        ui_hint = self._get_relationship_ui_hint(rel_type)

        return RelationshipInfo(
            name=rel_name,
            type=rel_type,
            local_table=table_name,
            remote_table=referred_table,
            local_columns=constrained_columns,
            remote_columns=referred_columns,
            association_table=association_table,
            back_populates=back_populates,
            cascade_options=self._determine_cascade_options(rel_type),
            lazy_loading=self._determine_lazy_loading(rel_type),
            display_name=display_name,
            description=description,
            cardinality_description=cardinality_desc,
            ui_hint=ui_hint
        )

    def _identify_association_tables(self):
        """Identify association tables for many-to-many relationships."""
        for table_name in self.metadata.tables:
            if self._is_association_table(table_name):
                self._association_tables.add(table_name)

    def _is_association_table(self, table_name: str) -> bool:
        """Determine if a table is an association table."""
        # Check naming convention
        if table_name.endswith('_assoc') or '_to_' in table_name:
            return True

        foreign_keys = self.inspector.get_foreign_keys(table_name)
        columns = self.inspector.get_columns(table_name)

        # Must have at least 2 foreign keys
        if len(foreign_keys) < 2:
            return False

        # Check if mostly foreign key columns
        fk_columns = {col for fk in foreign_keys for col in fk['constrained_columns']}
        non_fk_columns = [col for col in columns if col['name'] not in fk_columns]

        # Allow for id, timestamps, and a few metadata columns
        allowed_extra = {'id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'active'}
        extra_columns = [col for col in non_fk_columns if col['name'] not in allowed_extra]

        return len(extra_columns) <= 2

    def _determine_relationship_type(self, table_name: str, fk: Dict[str, Any]) -> RelationshipType:
        """Determine the type of relationship based on constraints and structure."""
        referred_table = fk['referred_table']
        constrained_columns = fk['constrained_columns']

        # Self-referencing
        if table_name == referred_table:
            return RelationshipType.SELF_REFERENCING

        # Many-to-many via association table
        if table_name in self._association_tables:
            return RelationshipType.MANY_TO_MANY

        # Check for unique constraints (one-to-one)
        unique_constraints = self.inspector.get_unique_constraints(table_name)
        pk_constraint = self.inspector.get_pk_constraint(table_name)
        pk_columns = set(pk_constraint['constrained_columns'])

        # One-to-one if FK is unique or part of PK
        if set(constrained_columns) == pk_columns:
            return RelationshipType.ONE_TO_ONE

        for constraint in unique_constraints:
            if set(constrained_columns).issubset(set(constraint['column_names'])):
                return RelationshipType.ONE_TO_ONE

        # Default to many-to-one
        return RelationshipType.MANY_TO_ONE

    def _categorize_column(self, column: Column, table_name: str) -> ColumnType:
        """Categorize a column based on its properties."""
        if column.primary_key:
            return ColumnType.PRIMARY_KEY
        elif column.foreign_keys:
            return ColumnType.FOREIGN_KEY
        elif isinstance(column.type, types.JSON):
            return ColumnType.JSON
        elif isinstance(column.type, types.ARRAY):
            return ColumnType.ARRAY
        elif isinstance(column.type, types.Enum):
            return ColumnType.ENUM
        elif isinstance(column.type, (types.LargeBinary, types.BLOB)):
            return ColumnType.BINARY
        elif isinstance(column.type, (types.Text, types.String)):
            return ColumnType.TEXT
        elif isinstance(column.type, (types.Integer, types.Numeric, types.Float)):
            return ColumnType.NUMERIC
        elif isinstance(column.type, (types.Date, types.DateTime, types.Time)):
            return ColumnType.DATE_TIME
        elif isinstance(column.type, types.Boolean):
            return ColumnType.BOOLEAN
        else:
            return ColumnType.TEXT  # Default

    def _suggest_widget_type(self, column: Column, category: ColumnType) -> str:
        """Suggest the appropriate widget type for a column."""
        column_name = column.name.lower()

        # Special name-based widgets
        if 'password' in column_name:
            return 'BS3PasswordFieldWidget'
        elif 'email' in column_name:
            return 'BS3TextFieldWidget'
        elif 'color' in column_name:
            return 'ColorPickerWidget'
        elif any(word in column_name for word in ['photo', 'image', 'picture']):
            return 'FileUploadWidget'
        elif 'code' in column_name and isinstance(column.type, types.Text):
            return 'CodeEditorWidget'
        elif 'chart' in column_name or 'graph' in column_name:
            return 'AdvancedChartsWidget'
        elif 'location' in column_name or 'gps' in column_name:
            return 'GPSTrackerWidget'
        elif 'qr' in column_name:
            return 'QrCodeWidget'

        # Type-based widgets
        if category == ColumnType.JSON:
            return 'JSONEditorWidget'
        elif category == ColumnType.ARRAY:
            return 'Select2ManyWidget'
        elif category == ColumnType.ENUM:
            return 'Select2Widget'
        elif category == ColumnType.BINARY:
            return 'FileUploadWidget'
        elif category == ColumnType.DATE_TIME:
            if isinstance(column.type, types.Date):
                return 'BS3DateFieldWidget'
            elif isinstance(column.type, types.DateTime):
                return 'BS3DateTimeFieldWidget'
            else:
                return 'TimePickerWidget'
        elif category == ColumnType.BOOLEAN:
            return 'CheckboxWidget'
        elif category == ColumnType.TEXT:
            if isinstance(column.type, types.Text) or (
                hasattr(column.type, 'length') and
                column.type.length and column.type.length > 200
            ):
                return 'BS3TextAreaFieldWidget'
            else:
                return 'BS3TextFieldWidget'
        elif category == ColumnType.FOREIGN_KEY:
            return 'Select2AJAXWidget'
        else:
            return 'BS3TextFieldWidget'  # Default

    def _generate_validation_rules(self, column: Column, category: ColumnType) -> List[str]:
        """Generate validation rules for a column."""
        rules = []

        if not column.nullable:
            rules.append('DataRequired()')

        if category == ColumnType.TEXT and hasattr(column.type, 'length') and column.type.length:
            rules.append(f'Length(max={column.type.length})')

        column_name = column.name.lower()
        if 'email' in column_name:
            rules.append('Email()')
        elif 'url' in column_name:
            rules.append('URL()')
        elif category == ColumnType.NUMERIC:
            rules.append('NumberRange()')

        return rules

    def get_all_tables(self) -> List[str]:
        """Get all table names."""
        return self.inspector.get_table_names()

    def _get_database_info(self) -> Dict[str, Any]:
        """Get basic database information."""
        return {
            'name': self.engine.url.database,
            'dialect': self.engine.dialect.name,
            'server_version': getattr(self.engine.dialect, 'server_version_info', 'Unknown'),
            'url': str(self.engine.url).replace(f":{self.engine.url.password}", ":****") if self.engine.url.password else str(self.engine.url)
        }

    def _get_database_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        tables = self.get_all_tables()
        total_tables = len(tables)
        association_tables = len(self._association_tables)
        regular_tables = total_tables - association_tables

        return {
            'total_tables': total_tables,
            'regular_tables': regular_tables,
            'association_tables': association_tables,
            'system_tables': len([t for t in tables if t.startswith('ab_')]),
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for the database structure."""
        recommendations = []

        stats = self._get_database_statistics()
        if stats['regular_tables'] > 20:
            recommendations.append("Consider using multiple Flask-AppBuilder blueprints to organize views")

        if stats['association_tables'] > 5:
            recommendations.append("Consider using API views for complex many-to-many relationships")

        return recommendations

    def _generate_display_name(self, table_name: str) -> str:
        """Generate a human-readable display name for a table."""
        return table_name.replace('_', ' ').title()

    def _generate_column_display_name(self, column_name: str) -> str:
        """Generate a human-readable display name for a column."""
        return column_name.replace('_', ' ').title()

    def _generate_table_description(self, table_name: str, columns: List[ColumnInfo]) -> str:
        """Generate a description for a table."""
        return f"Manages {table_name.replace('_', ' ')} data with {len(columns)} columns"

    def _generate_column_description(self, column: Column, category: ColumnType, comment: Optional[str]) -> str:
        """Generate a description for a column."""
        if comment:
            return comment
        return f"{category.value.title()} field for {column.name.replace('_', ' ')}"

    def _categorize_table(self, table_name: str, columns: List[ColumnInfo]) -> str:
        """Categorize a table based on its structure and name."""
        name_lower = table_name.lower()

        if any(word in name_lower for word in ['user', 'account', 'profile']):
            return 'User Management'
        elif any(word in name_lower for word in ['order', 'sale', 'purchase', 'transaction']):
            return 'Commerce'
        elif any(word in name_lower for word in ['product', 'item', 'catalog']):
            return 'Inventory'
        elif any(word in name_lower for word in ['log', 'audit', 'history']):
            return 'Audit'
        elif table_name in self._association_tables:
            return 'Association'
        else:
            return 'General'

    def _get_table_icon(self, category: str, table_name: str) -> str:
        """Get an appropriate icon for a table."""
        icon_map = {
            'User Management': 'fa-users',
            'Commerce': 'fa-shopping-cart',
            'Inventory': 'fa-boxes',
            'Audit': 'fa-history',
            'Association': 'fa-link',
            'General': 'fa-table'
        }
        return icon_map.get(category, 'fa-table')

    def _estimate_table_rows(self, table_name: str) -> int:
        """Estimate the number of rows in a table safely."""
        try:
            # Use SQLAlchemy 2.x compatible syntax with proper SQL identifier handling
            from sqlalchemy import text, select, func
            from sqlalchemy.sql import table
            
            # Create a table reference for safe SQL generation
            table_ref = table(table_name)
            stmt = select(func.count()).select_from(table_ref)
            
            with self.engine.connect() as conn:
                result = conn.execute(stmt)
                return result.scalar() or 0
                
        except Exception as e:
            logger.warning(f"Could not estimate rows for table {table_name}: {e}")
            return 0

    def _suggest_view_types(self, columns: List[ColumnInfo], relationships: List[RelationshipInfo], is_association: bool) -> List[str]:
        """Suggest appropriate view types for a table."""
        view_types = ['ModelView']  # Always include basic model view

        if not is_association:
            view_types.extend(['MultipleView', 'ReportView', 'ApiView'])

            # Chart view if has numeric and date columns
            has_numeric = any(col.category == ColumnType.NUMERIC for col in columns)
            has_date = any(col.category == ColumnType.DATE_TIME for col in columns)
            if has_numeric and has_date:
                view_types.append('ChartView')

            # Calendar view if has date columns
            if has_date:
                view_types.append('CalendarView')

            # Wizard view for complex forms
            if len(columns) > 8:
                view_types.append('WizardView')

            # Master-detail for relationships
            if relationships:
                view_types.append('MasterDetailView')

        return view_types

    def _assess_security_level(self, columns: List[ColumnInfo]) -> str:
        """Assess the security level needed for a table."""
        sensitive_patterns = ['password', 'ssn', 'credit', 'bank', 'secret', 'key', 'token']

        for column in columns:
            if any(pattern in column.name.lower() for pattern in sensitive_patterns):
                return 'HIGH'

        user_patterns = ['user', 'account', 'profile', 'email']
        if any(pattern in column.name.lower() for pattern in user_patterns for column in columns):
            return 'MEDIUM'

        return 'LOW'

    def _get_table_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all constraints for a table."""
        constraints = []

        # Primary key
        pk = self.inspector.get_pk_constraint(table_name)
        if pk['constrained_columns']:
            constraints.append({'type': 'primary_key', 'data': pk})

        # Foreign keys
        for fk in self.inspector.get_foreign_keys(table_name):
            constraints.append({'type': 'foreign_key', 'data': fk})

        # Unique constraints
        for unique in self.inspector.get_unique_constraints(table_name):
            constraints.append({'type': 'unique', 'data': unique})

        # Check constraints
        for check in self.inspector.get_check_constraints(table_name):
            constraints.append({'type': 'check', 'data': check})

        return constraints

    def _generate_relationship_name(self, table_name: str, referred_table: str,
                                  constrained_columns: List[str], rel_type: RelationshipType) -> str:
        """Generate a meaningful relationship name."""
        if len(constrained_columns) == 1:
            col_name = constrained_columns[0]
            base_name = col_name.replace('_id', '').replace('_fk', '')

            if base_name == referred_table.lower():
                base_name = referred_table.lower()

            if rel_type in [RelationshipType.ONE_TO_MANY, RelationshipType.MANY_TO_MANY]:
                return p.plural(base_name)
            else:
                return base_name
        else:
            # Multiple columns - create composite name
            return '_'.join(constrained_columns).replace('_id', '').replace('_fk', '')

    def _generate_back_populates_name(self, table_name: str, referred_table: str, rel_type: RelationshipType) -> str:
        """Generate the back_populates name for relationships."""
        if rel_type in [RelationshipType.ONE_TO_MANY, RelationshipType.MANY_TO_MANY]:
            return p.plural(table_name.lower())
        else:
            return table_name.lower()

    def _find_association_table(self, table1: str, table2: str) -> Optional[str]:
        """Find association table for many-to-many relationship."""
        for assoc_table in self._association_tables:
            fks = self.inspector.get_foreign_keys(assoc_table)
            referred_tables = {fk['referred_table'] for fk in fks}
            if table1 in referred_tables and table2 in referred_tables:
                return assoc_table
        return None

    def _generate_relationship_display_name(self, rel_name: str, rel_type: RelationshipType) -> str:
        """Generate display name for relationship."""
        return rel_name.replace('_', ' ').title()

    def _generate_relationship_description(self, local_table: str, remote_table: str, rel_type: RelationshipType) -> str:
        """Generate description for relationship."""
        type_descriptions = {
            RelationshipType.ONE_TO_ONE: f"One {local_table} has one {remote_table}",
            RelationshipType.ONE_TO_MANY: f"One {remote_table} has many {local_table}",
            RelationshipType.MANY_TO_ONE: f"Many {local_table} belong to one {remote_table}",
            RelationshipType.MANY_TO_MANY: f"Many {local_table} are related to many {remote_table}",
            RelationshipType.SELF_REFERENCING: f"{local_table} references itself",
        }
        return type_descriptions.get(rel_type, f"Relationship between {local_table} and {remote_table}")

    def _get_cardinality_description(self, rel_type: RelationshipType) -> str:
        """Get cardinality description for relationship."""
        return {
            RelationshipType.ONE_TO_ONE: "1:1",
            RelationshipType.ONE_TO_MANY: "1:N",
            RelationshipType.MANY_TO_ONE: "N:1",
            RelationshipType.MANY_TO_MANY: "N:N",
            RelationshipType.SELF_REFERENCING: "Self",
        }.get(rel_type, "Unknown")

    def _get_relationship_ui_hint(self, rel_type: RelationshipType) -> str:
        """Get UI hint for relationship."""
        return {
            RelationshipType.ONE_TO_ONE: "Use inline form or modal",
            RelationshipType.ONE_TO_MANY: "Use related list view",
            RelationshipType.MANY_TO_ONE: "Use select widget",
            RelationshipType.MANY_TO_MANY: "Use multiple select or tags",
            RelationshipType.SELF_REFERENCING: "Use tree view or hierarchy",
        }.get(rel_type, "Standard relationship display")

    def _determine_cascade_options(self, rel_type: RelationshipType) -> List[str]:
        """Determine appropriate cascade options."""
        if rel_type == RelationshipType.ONE_TO_MANY:
            return ['save-update', 'delete']
        elif rel_type == RelationshipType.MANY_TO_ONE:
            return ['save-update']
        else:
            return []

    def _determine_lazy_loading(self, rel_type: RelationshipType) -> str:
        """Determine appropriate lazy loading strategy."""
        if rel_type == RelationshipType.MANY_TO_MANY:
            return 'dynamic'
        else:
            return 'select'

    def _suggest_form_field_type(self, column: Column, category: ColumnType) -> str:
        """Suggest form field type for a column."""
        if category == ColumnType.FOREIGN_KEY:
            return 'QuerySelectField'
        elif category == ColumnType.BOOLEAN:
            return 'BooleanField'
        elif category == ColumnType.DATE_TIME:
            if isinstance(column.type, types.Date):
                return 'DateField'
            elif isinstance(column.type, types.DateTime):
                return 'DateTimeField'
            else:
                return 'TimeField'
        elif category == ColumnType.NUMERIC:
            if isinstance(column.type, types.Integer):
                return 'IntegerField'
            else:
                return 'FloatField'
        elif category == ColumnType.TEXT:
            if isinstance(column.type, types.Text):
                return 'TextAreaField'
            else:
                return 'StringField'
        else:
            return 'StringField'

    def analyze_master_detail_patterns(self, table_name: str) -> List[MasterDetailInfo]:
        """
        Analyze potential master-detail patterns for a table.
        
        Args:
            table_name: Parent table to analyze
            
        Returns:
            List of suitable master-detail patterns
        """
        master_detail_patterns = []
        
        # Get all tables that reference this table (potential children)
        all_tables = self.get_all_tables()
        
        for potential_child in all_tables:
            if potential_child == table_name:
                continue
                
            child_relationships = self._analyze_relationships(potential_child)
            
            for relationship in child_relationships:
                if (relationship.remote_table == table_name and 
                    relationship.type == RelationshipType.MANY_TO_ONE):
                    
                    # Analyze if this is suitable for master-detail
                    master_detail_info = self._analyze_master_detail_suitability(
                        table_name, potential_child, relationship
                    )
                    
                    if master_detail_info:
                        master_detail_patterns.append(master_detail_info)
        
        return master_detail_patterns
    
    def _analyze_master_detail_suitability(self, parent_table: str, child_table: str, 
                                         relationship: RelationshipInfo) -> Optional[MasterDetailInfo]:
        """
        Determine if a relationship is suitable for master-detail view.
        
        Args:
            parent_table: Parent table name
            child_table: Child table name  
            relationship: Relationship information
            
        Returns:
            MasterDetailInfo if suitable, None otherwise
        """
        try:
            # Get child table info
            child_info = self.analyze_table(child_table)
            parent_info = self.analyze_table(parent_table)
            
            # Check suitability criteria
            is_suitable = self._is_suitable_for_master_detail(child_info, parent_info, relationship)
            
            if not is_suitable:
                return None
                
            # Estimate child record count
            expected_count = self._estimate_child_record_count(parent_table, child_table, relationship)
            
            # Determine display fields
            child_display_fields = self._get_inline_display_fields(child_info)
            parent_display_fields = self._get_parent_display_fields(parent_info)
            
            # UI Configuration
            ui_config = self._determine_inline_ui_config(child_info, expected_count)
            
            return MasterDetailInfo(
                parent_table=parent_table,
                child_table=child_table,
                relationship=relationship,
                is_suitable_for_inline=True,
                expected_child_count=expected_count,
                child_display_fields=child_display_fields,
                parent_display_fields=parent_display_fields,
                inline_edit_suitable=ui_config['inline_edit_suitable'],
                supports_bulk_operations=ui_config['supports_bulk_operations'],
                default_child_count=ui_config['default_child_count'],
                min_child_forms=ui_config['min_child_forms'], 
                max_child_forms=ui_config['max_child_forms'],
                enable_sorting=ui_config['enable_sorting'],
                enable_deletion=ui_config['enable_deletion'],
                child_form_layout=ui_config['child_form_layout']
            )
            
        except Exception as e:
            # Log error and continue
            print(f"Error analyzing master-detail for {parent_table}->{child_table}: {e}")
            return None
    
    def _is_suitable_for_master_detail(self, child_info: TableInfo, parent_info: TableInfo, 
                                     relationship: RelationshipInfo) -> bool:
        """
        Determine if a relationship is suitable for master-detail pattern.
        
        Criteria:
        - Child table has reasonable number of columns (3-15)
        - Child table is not an association table
        - Relationship is not self-referencing
        - Child table doesn't have too many complex relationships
        - Parent table has a clear primary display field
        """
        # Basic checks
        if child_info.is_association_table:
            return False
            
        if relationship.type == RelationshipType.SELF_REFERENCING:
            return False
        
        # Column count check
        non_system_columns = [col for col in child_info.columns 
                            if not col.name.lower().startswith(('created_', 'updated_', 'deleted_'))]
        if len(non_system_columns) < 2 or len(non_system_columns) > 15:
            return False
            
        # Check if child table has too many foreign keys (complex relationship)
        foreign_key_count = len([col for col in child_info.columns if col.foreign_key])
        if foreign_key_count > 3:
            return False
            
        # Check if parent has a good display field
        parent_display_fields = [col for col in parent_info.columns 
                               if col.name.lower() in ['name', 'title', 'label', 'code']]
        if not parent_display_fields:
            return False
            
        return True
    
    def _estimate_child_record_count(self, parent_table: str, child_table: str, 
                                   relationship: RelationshipInfo) -> str:
        """
        Estimate expected number of child records per parent.
        
        Returns:
            "few" (1-5), "moderate" (6-20), "many" (20+)
        """
        try:
            # Try to get actual statistics if available
            parent_count = self._estimate_table_rows(parent_table)
            child_count = self._estimate_table_rows(child_table)
            
            if parent_count > 0:
                ratio = child_count / parent_count
                if ratio <= 5:
                    return "few"
                elif ratio <= 20:
                    return "moderate"
                else:
                    return "many"
        except:
            pass
            
        # Fallback to heuristic based on table name patterns
        child_name = child_table.lower()
        
        # Tables likely to have few children
        few_patterns = ['address', 'profile', 'setting', 'preference', 'config']
        if any(pattern in child_name for pattern in few_patterns):
            return "few"
            
        # Tables likely to have many children
        many_patterns = ['log', 'event', 'transaction', 'history', 'audit', 'item']
        if any(pattern in child_name for pattern in many_patterns):
            return "many"
            
        # Default to moderate
        return "moderate"
    
    def _get_inline_display_fields(self, child_info: TableInfo) -> List[str]:
        """Get the most important fields to display in inline forms."""
        display_fields = []
        
        # Priority order for field selection
        priority_patterns = [
            ['name', 'title', 'label'],
            ['description', 'comment', 'note'],
            ['code', 'sku', 'identifier'],
            ['amount', 'price', 'value', 'quantity'],
            ['status', 'type', 'category'],
            ['email', 'phone', 'contact'],
            ['date', 'created_at', 'updated_at']
        ]
        
        # Select up to 4 most relevant fields
        for pattern_group in priority_patterns:
            if len(display_fields) >= 4:
                break
                
            for column in child_info.columns:
                if (len(display_fields) < 4 and 
                    not column.primary_key and 
                    not column.foreign_key and
                    column.name not in display_fields):
                    
                    col_name_lower = column.name.lower()
                    if any(pattern in col_name_lower for pattern in pattern_group):
                        display_fields.append(column.name)
                        break
        
        # If we don't have enough fields, add non-foreign key fields
        if len(display_fields) < 2:
            for column in child_info.columns:
                if (len(display_fields) < 4 and 
                    not column.primary_key and 
                    not column.foreign_key and
                    column.name not in display_fields):
                    display_fields.append(column.name)
        
        return display_fields[:4]  # Maximum 4 fields for inline display
    
    def _get_parent_display_fields(self, parent_info: TableInfo) -> List[str]:
        """Get key fields to display in parent record."""
        display_fields = []
        
        # Find the best display field for the parent
        for column in parent_info.columns:
            col_name_lower = column.name.lower()
            if col_name_lower in ['name', 'title', 'label']:
                display_fields.append(column.name)
                break
        
        # Add additional context fields
        for column in parent_info.columns:
            if len(display_fields) >= 3:
                break
                
            col_name_lower = column.name.lower()
            if (not column.primary_key and 
                column.name not in display_fields and
                col_name_lower in ['code', 'status', 'type', 'category', 'description']):
                display_fields.append(column.name)
        
        return display_fields
    
    def _determine_inline_ui_config(self, child_info: TableInfo, expected_count: str) -> Dict[str, Any]:
        """
        Determine UI configuration for inline formsets.
        
        Args:
            child_info: Child table information
            expected_count: Expected number of child records
            
        Returns:
            Dictionary with UI configuration
        """
        config = {
            'inline_edit_suitable': True,
            'supports_bulk_operations': True,
            'enable_sorting': True,
            'enable_deletion': True
        }
        
        # Configure based on expected count
        if expected_count == "few":
            config.update({
                'default_child_count': 3,
                'min_child_forms': 1,
                'max_child_forms': 10,
                'child_form_layout': 'stacked'
            })
        elif expected_count == "moderate":
            config.update({
                'default_child_count': 5,
                'min_child_forms': 0,
                'max_child_forms': 25,
                'child_form_layout': 'tabular'
            })
        else:  # many
            config.update({
                'default_child_count': 0,  # Don't pre-create forms
                'min_child_forms': 0,
                'max_child_forms': 50,
                'child_form_layout': 'accordion',
                'inline_edit_suitable': False  # Too many for inline editing
            })
        
        # Adjust based on child table complexity
        field_count = len([col for col in child_info.columns if not col.primary_key])
        
        if field_count > 8:
            config['child_form_layout'] = 'accordion'
        elif field_count > 12:
            config['inline_edit_suitable'] = False
            
        # Disable bulk operations for complex forms
        if field_count > 10 or len([col for col in child_info.columns if col.foreign_key]) > 2:
            config['supports_bulk_operations'] = False
            
        return config

    def get_relationship_view_variations(self, table_name: str) -> Dict[str, List[str]]:
        """
        Get suggested view variations based on foreign key relationships.
        
        Args:
            table_name: Table to analyze
            
        Returns:
            Dictionary mapping relationship types to suggested view types
        """
        variations = {
            'standard_views': ['ModelView', 'Api'],
            'relationship_views': [],
            'master_detail_views': [],
            'lookup_views': [],
            'reference_views': []
        }
        
        table_info = self.analyze_table(table_name)
        relationships = self._analyze_relationships(table_name)
        master_detail_patterns = self.analyze_master_detail_patterns(table_name)
        
        # Add master-detail views
        for pattern in master_detail_patterns:
            view_name = f"{self._to_pascal_case(table_name)}{self._to_pascal_case(pattern.child_table)}MasterDetailView"
            variations['master_detail_views'].append(view_name)
        
        # Add relationship-specific views
        foreign_key_count = len([col for col in table_info.columns if col.foreign_key])
        
        if foreign_key_count > 0:
            # Lookup view for tables with many foreign keys
            if foreign_key_count >= 2:
                variations['lookup_views'].append(f"{self._to_pascal_case(table_name)}LookupView")
            
            # Reference views for each significant relationship
            for relationship in relationships:
                if relationship.type in [RelationshipType.MANY_TO_ONE, RelationshipType.ONE_TO_ONE]:
                    ref_view_name = f"{self._to_pascal_case(table_name)}By{self._to_pascal_case(relationship.remote_table)}View"
                    variations['reference_views'].append(ref_view_name)
        
        # Add relationship navigation views
        if len(relationships) > 1:
            variations['relationship_views'].append(f"{self._to_pascal_case(table_name)}RelationshipView")
        
        return variations

    def _to_pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        return ''.join(word.capitalize() for word in snake_str.split('_'))
