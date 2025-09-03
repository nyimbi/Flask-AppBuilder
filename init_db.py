#!/usr/bin/env python3
"""
Database Initialization Script
Flask-AppBuilder Apache AGE Graph Analytics Platform

This script initializes the complete database schema, creates admin user,
and sets up the initial graph structures for the platform.
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask
from flask_appbuilder import AppBuilder, SQLA
from flask_appbuilder.security.sqla.manager import SecurityManager
import psycopg2
from psycopg2 import sql

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """Database initialization and setup manager"""
    
    def __init__(self):
        self.app = None
        self.db = None
        self.appbuilder = None
        
    def create_flask_app(self):
        """Create and configure Flask application"""
        logger.info("🚀 Creating Flask application...")
        
        self.app = Flask(__name__)
        
        # Load configuration
        database_uri = os.environ.get(
            'DATABASE_URI',
            'postgresql://graph_admin:password@localhost:5432/graph_analytics_db'
        )
        
        self.app.config.update({
            'SQLALCHEMY_DATABASE_URI': database_uri,
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-key-change-in-production'),
            'SECURITY_PASSWORD_SALT': os.environ.get('SECURITY_PASSWORD_SALT', 'salt'),
            'WTF_CSRF_ENABLED': False,  # Disable for initialization
        })
        
        # Initialize extensions
        self.db = SQLA(self.app)
        self.appbuilder = AppBuilder(
            self.app, 
            self.db.session, 
            security_manager_class=SecurityManager
        )
        
        logger.info("✅ Flask application created successfully")
        return self.app
    
    def check_database_connection(self):
        """Check database connectivity"""
        logger.info("🔍 Checking database connection...")
        
        try:
            database_uri = self.app.config['SQLALCHEMY_DATABASE_URI']
            
            # Parse database URI
            from urllib.parse import urlparse
            parsed = urlparse(database_uri)
            
            # Test connection
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],  # Remove leading /
                user=parsed.username,
                password=parsed.password
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            logger.info(f"✅ Database connection successful: {version}")
            
            # Check for Apache AGE extension
            cursor.execute("SELECT * FROM pg_extension WHERE extname = 'age';")
            age_ext = cursor.fetchone()
            if age_ext:
                logger.info("✅ Apache AGE extension is installed")
            else:
                logger.warning("⚠️  Apache AGE extension not found - will be installed")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def initialize_database_schema(self):
        """Initialize Flask-AppBuilder database schema"""
        logger.info("📊 Initializing database schema...")
        
        try:
            with self.app.app_context():
                # Create all tables
                self.db.create_all()
                logger.info("✅ Database tables created successfully")
                
                # Initialize security roles and permissions
                self.appbuilder.sm.sync_role_definitions()
                logger.info("✅ Security roles and permissions synchronized")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Schema initialization failed: {e}")
            return False
    
    def initialize_apache_age(self):
        """Initialize Apache AGE extension and create graphs"""
        logger.info("🔧 Initializing Apache AGE extension...")
        
        try:
            # Run AGE initialization script
            init_script_path = Path(__file__).parent / 'init-scripts' / '01-init-age.sql'
            
            if not init_script_path.exists():
                logger.error(f"❌ Initialization script not found: {init_script_path}")
                return False
            
            # Execute initialization script
            database_uri = self.app.config['SQLALCHEMY_DATABASE_URI']
            from urllib.parse import urlparse
            parsed = urlparse(database_uri)
            
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password
            )
            
            cursor = conn.cursor()
            
            with open(init_script_path, 'r') as f:
                sql_script = f.read()
            
            # Execute script
            cursor.execute(sql_script)
            conn.commit()
            
            logger.info("✅ Apache AGE extension initialized successfully")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Apache AGE initialization failed: {e}")
            return False
    
    def create_sample_data(self):
        """Create sample data for demonstration"""
        logger.info("📝 Creating sample data...")
        
        try:
            # Run sample data script
            sample_script_path = Path(__file__).parent / 'init-scripts' / '02-sample-data.sql'
            
            if not sample_script_path.exists():
                logger.warning("⚠️  Sample data script not found, skipping...")
                return True
            
            database_uri = self.app.config['SQLALCHEMY_DATABASE_URI']
            from urllib.parse import urlparse
            parsed = urlparse(database_uri)
            
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password
            )
            
            cursor = conn.cursor()
            
            with open(sample_script_path, 'r') as f:
                sql_script = f.read()
            
            cursor.execute(sql_script)
            conn.commit()
            
            logger.info("✅ Sample data created successfully")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Sample data creation failed: {e}")
            return False
    
    def create_admin_user(self):
        """Create initial admin user"""
        logger.info("👤 Creating admin user...")
        
        try:
            with self.app.app_context():
                # Check if admin user already exists
                admin_user = self.appbuilder.sm.find_user(username='admin')
                if admin_user:
                    logger.info("ℹ️  Admin user already exists, skipping creation")
                    return True
                
                # Get admin role
                admin_role = self.appbuilder.sm.find_role("Admin")
                if not admin_role:
                    logger.error("❌ Admin role not found")
                    return False
                
                # Create admin user with default credentials
                admin_password = os.environ.get('ADMIN_PASSWORD')
                if not admin_password:
                    raise ValueError(
                        "ADMIN_PASSWORD environment variable is required. "
                        "Please set a secure password (minimum 12 characters, "
                        "including uppercase, lowercase, numbers, and special characters)."
                    )
                
                user = self.appbuilder.sm.add_user(
                    username='admin',
                    first_name='Admin',
                    last_name='User',
                    email='admin@graph-analytics.local',
                    role=admin_role,
                    password=admin_password
                )
                
                if user:
                    logger.info("✅ Admin user created successfully")
                    logger.info("📧 Username: admin")
                    logger.info("🔑 Password: admin123! (CHANGE THIS IN PRODUCTION)")
                    return True
                else:
                    logger.error("❌ Failed to create admin user")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Admin user creation failed: {e}")
            return False
    
    def verify_installation(self):
        """Verify the installation is working correctly"""
        logger.info("✅ Verifying installation...")
        
        try:
            with self.app.app_context():
                # Test database connection
                result = self.db.session.execute("SELECT 1").fetchone()
                if not result:
                    logger.error("❌ Database connection test failed")
                    return False
                
                # Test Apache AGE
                from flask_appbuilder.database.graph_manager import GraphDatabaseManager
                graph_manager = GraphDatabaseManager()
                
                # Test graph creation
                test_result = graph_manager.execute_cypher_query(
                    "MATCH (n) RETURN count(n) as node_count",
                    graph_name="analytics_graph"
                )
                
                if test_result:
                    logger.info("✅ Apache AGE functionality verified")
                else:
                    logger.warning("⚠️  Apache AGE test query failed")
                
                # Check user count
                user_count = self.appbuilder.sm.get_all_users().count()
                logger.info(f"✅ Found {user_count} user(s) in the system")
                
                # Check roles count
                role_count = len(self.appbuilder.sm.get_all_roles())
                logger.info(f"✅ Found {role_count} role(s) configured")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Installation verification failed: {e}")
            return False
    
    def run_full_initialization(self):
        """Run complete database initialization process"""
        logger.info("🎯 Starting complete database initialization...")
        
        steps = [
            ("Create Flask App", self.create_flask_app),
            ("Check Database Connection", self.check_database_connection),
            ("Initialize Database Schema", self.initialize_database_schema),
            ("Initialize Apache AGE", self.initialize_apache_age),
            ("Create Sample Data", self.create_sample_data),
            ("Create Admin User", self.create_admin_user),
            ("Verify Installation", self.verify_installation),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"➡️  {step_name}...")
            
            if step_name == "Create Flask App":
                step_func()  # This returns the app, not boolean
                continue
            
            success = step_func()
            if not success:
                logger.error(f"❌ Step failed: {step_name}")
                return False
            
            logger.info(f"✅ {step_name} completed")
        
        logger.info("🎉 Database initialization completed successfully!")
        logger.info("🚀 The Flask-AppBuilder Apache AGE Graph Analytics Platform is ready!")
        logger.info("🔗 Access the application at: http://localhost:8080")
        logger.info("👤 Login with username: admin, password: [set via ADMIN_PASSWORD env var]")
        
        return True


def main():
    """Main initialization function"""
    print("="*80)
    print("🚀 FLASK-APPBUILDER APACHE AGE GRAPH ANALYTICS PLATFORM")
    print("   DATABASE INITIALIZATION")
    print("="*80)
    
    # Check environment variables
    required_vars = ['DATABASE_URI', 'SECRET_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.warning(f"⚠️  Missing environment variables: {missing_vars}")
        logger.info("Using default values (not recommended for production)")
    
    # Initialize database
    initializer = DatabaseInitializer()
    success = initializer.run_full_initialization()
    
    if success:
        print("="*80)
        print("🎉 INITIALIZATION SUCCESSFUL!")
        print("   Your graph analytics platform is ready to use.")
        print("="*80)
        return 0
    else:
        print("="*80)
        print("❌ INITIALIZATION FAILED!")
        print("   Please check the logs above for details.")
        print("="*80)
        return 1


if __name__ == '__main__':
    sys.exit(main())