#!/usr/bin/env python3
"""
Import API Scrip Master data from MySQL to Supabase
This enables security ID mapping for Dhan API execution
"""

import os
import sys
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
import logging

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('/Users/jaykrish/Documents/digitalocean/.env')

from database import SupabaseIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScripMasterImporter:
    def __init__(self):
        """Initialize with database connections"""
        self.supabase = SupabaseIntegration(logger)
        if not self.supabase.client:
            raise Exception("Failed to connect to Supabase")
    
    def create_scrip_master_table(self):
        """Create api_scrip_master table in Supabase if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS api_scrip_master (
            id SERIAL PRIMARY KEY,
            SEM_SMST_SECURITY_ID INTEGER UNIQUE NOT NULL,
            SEM_TRADING_SYMBOL VARCHAR(100),
            SEM_INSTRUMENT_NAME VARCHAR(100),
            SEM_SEGMENT VARCHAR(50),
            SEM_EXCH_INSTRUMENT_TYPE VARCHAR(50),
            SEM_OPTION_TYPE VARCHAR(10),
            SEM_STRIKE_PRICE DECIMAL(10,2),
            SEM_EXPIRY_DATE DATE,
            SEM_LOT_UNITS INTEGER,
            SEM_CUSTOM_SYMBOL VARCHAR(100),
            SEM_EXPIRY_FLAG VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX idx_scrip_symbol ON api_scrip_master(SEM_TRADING_SYMBOL);
        CREATE INDEX idx_scrip_expiry ON api_scrip_master(SEM_EXPIRY_DATE);
        CREATE INDEX idx_scrip_strike ON api_scrip_master(SEM_STRIKE_PRICE);
        CREATE INDEX idx_scrip_option_type ON api_scrip_master(SEM_OPTION_TYPE);
        """
        
        logger.info("Note: Table creation should be done via Supabase SQL editor")
        logger.info("SQL for table creation:")
        print(create_table_sql)
        return True
    
    def fetch_mysql_data(self):
        """Fetch data from MySQL api_scrip_master"""
        try:
            # MySQL connection
            conn = mysql.connector.connect(
                host='mydb.cb04giyquztt.ap-south-1.rds.amazonaws.com',
                user='admin',
                password='Pest1234',
                database='mydb'
            )
            cursor = conn.cursor(dictionary=True)
            
            # Fetch relevant option data
            query = """
            SELECT 
                SEM_SMST_SECURITY_ID,
                SEM_TRADING_SYMBOL,
                SEM_INSTRUMENT_NAME,
                SEM_SEGMENT,
                SEM_EXCH_INSTRUMENT_TYPE,
                SEM_OPTION_TYPE,
                SEM_STRIKE_PRICE,
                SEM_EXPIRY_DATE,
                SEM_LOT_UNITS,
                SEM_CUSTOM_SYMBOL,
                SEM_EXPIRY_FLAG
            FROM api_scrip_master
            WHERE SEM_SEGMENT = 'D'
            AND SEM_OPTION_TYPE IN ('CE', 'PE')
            AND SEM_EXPIRY_DATE >= CURDATE()
            ORDER BY SEM_EXPIRY_DATE, SEM_TRADING_SYMBOL, SEM_STRIKE_PRICE
            """
            
            cursor.execute(query)
            data = cursor.fetchall()
            
            logger.info(f"Fetched {len(data)} records from MySQL")
            return data
            
        except Exception as e:
            logger.error(f"MySQL fetch error: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def import_to_supabase(self, data):
        """Import data to Supabase"""
        if not data:
            logger.warning("No data to import")
            return
        
        batch_size = 100
        total_imported = 0
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            
            # Prepare batch for insertion
            insert_data = []
            for record in batch:
                # Convert date to string format
                expiry_date = record['SEM_EXPIRY_DATE']
                if expiry_date:
                    expiry_date = expiry_date.strftime('%Y-%m-%d') if hasattr(expiry_date, 'strftime') else str(expiry_date)
                
                insert_data.append({
                    'SEM_SMST_SECURITY_ID': record['SEM_SMST_SECURITY_ID'],
                    'SEM_TRADING_SYMBOL': record['SEM_TRADING_SYMBOL'],
                    'SEM_INSTRUMENT_NAME': record['SEM_INSTRUMENT_NAME'],
                    'SEM_SEGMENT': record['SEM_SEGMENT'],
                    'SEM_EXCH_INSTRUMENT_TYPE': record['SEM_EXCH_INSTRUMENT_TYPE'],
                    'SEM_OPTION_TYPE': record['SEM_OPTION_TYPE'],
                    'SEM_STRIKE_PRICE': float(record['SEM_STRIKE_PRICE']) if record['SEM_STRIKE_PRICE'] else None,
                    'SEM_EXPIRY_DATE': expiry_date,
                    'SEM_LOT_UNITS': record['SEM_LOT_UNITS'],
                    'SEM_CUSTOM_SYMBOL': record['SEM_CUSTOM_SYMBOL'],
                    'SEM_EXPIRY_FLAG': record['SEM_EXPIRY_FLAG']
                })
            
            try:
                # Upsert to handle duplicates
                result = self.supabase.client.table('api_scrip_master').upsert(
                    insert_data,
                    on_conflict='SEM_SMST_SECURITY_ID'
                ).execute()
                
                if result.data:
                    total_imported += len(result.data)
                    logger.info(f"Imported batch {i//batch_size + 1}: {len(result.data)} records")
                
            except Exception as e:
                logger.error(f"Batch import error: {e}")
                continue
        
        logger.info(f"Total records imported: {total_imported}")
        return total_imported
    
    def verify_import(self, sample_symbol='NIFTY'):
        """Verify the import by checking some sample data"""
        try:
            result = self.supabase.client.table('api_scrip_master').select(
                'SEM_TRADING_SYMBOL, SEM_OPTION_TYPE, SEM_STRIKE_PRICE, SEM_EXPIRY_DATE'
            ).like('SEM_TRADING_SYMBOL', f'%{sample_symbol}%').limit(5).execute()
            
            if result.data:
                logger.info(f"\nSample data for {sample_symbol}:")
                for record in result.data:
                    logger.info(f"  {record['SEM_TRADING_SYMBOL']} {record['SEM_STRIKE_PRICE']} {record['SEM_OPTION_TYPE']} Exp: {record['SEM_EXPIRY_DATE']}")
            
        except Exception as e:
            logger.error(f"Verification error: {e}")

def main():
    """Main import function"""
    try:
        importer = ScripMasterImporter()
        
        # Step 1: Show table creation SQL
        logger.info("Step 1: Create table in Supabase")
        importer.create_scrip_master_table()
        
        confirm = input("\nHave you created the table in Supabase? (y/n): ")
        if confirm.lower() != 'y':
            logger.info("Please create the table first using the SQL above in Supabase SQL editor")
            return
        
        # Step 2: Fetch data from MySQL
        logger.info("\nStep 2: Fetching data from MySQL...")
        mysql_data = importer.fetch_mysql_data()
        
        if not mysql_data:
            logger.error("No data fetched from MySQL")
            return
        
        # Step 3: Import to Supabase
        logger.info(f"\nStep 3: Importing {len(mysql_data)} records to Supabase...")
        imported = importer.import_to_supabase(mysql_data)
        
        # Step 4: Verify
        logger.info("\nStep 4: Verifying import...")
        importer.verify_import('NIFTY')
        importer.verify_import('BANKNIFTY')
        
        logger.info("\nImport completed successfully!")
        
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()