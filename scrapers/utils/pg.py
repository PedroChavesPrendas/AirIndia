import os
import psycopg2
from utils.log import get_logger

logger = get_logger()

postgres_host = os.getenv("POSTGRES_HOST")
postgres_db = os.getenv("POSTGRES_DB")
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASS")
postgres_port = os.getenv("POSTGRES_PORT")

conn = psycopg2.connect(
    host=postgres_host,
    database=postgres_db,
    port=postgres_port,
    user=postgres_user,
    password=postgres_password
)

def update_login_record(id, status, number, update_time):

    with conn, conn.cursor() as cursor:
        # Construct the UPDATE query
        update_querry = """
            UPDATE airline_engine_scraper_login set 
            valid = %s, files_count = %s, last_ran = %s
            where id = %s;
        """
        # Execute the UPDATE query with the sample data
        cursor.execute(update_querry, (status, number, update_time, id))
        # Commit the transaction
        conn.commit()
        
    logger.info(f"Updated login table for {id}")
    
def update_login_record_new(id, status, number, update_time):

    with conn.cursor() as cursor:
                # Construct the UPDATE query
        update_querry = """
            UPDATE airline_engine_scraper_login set 
            valid = %s, files_count = %s, last_ran = %s
            where id = %s;
        """
        # Execute the UPDATE query with the sample data

        logger.info(f"Updated login table for {id}")
        try:
            cursor.execute(update_querry, (status, number, update_time, id))
            # Commit the transaction
            conn.commit()
            
        except Exception as e:
            logger.exception(f'Error while inserting File : {e}')
            



def insert_details(id, email, password, fromdate, todate, status):
    with conn.cursor() as cursor:
        insert_query = """
        INSERT INTO user_details (id, email, pass, fromdate, todate, status)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        # Log the data types and values before insertion
        logger.debug(f"Preparing to insert data: ID={id} ({type(id)}), email={email} ({type(email)}), "
                     f"password=**** ({type(password)}), fromdate={fromdate} ({type(fromdate)}), "
                     f"todate={todate} ({type(todate)}),  ( status={status} ({type(status)})")

        try:
            cursor.execute(insert_query, (id, email, password, fromdate, todate, status))
            conn.commit()
            logger.info(f"Inserted details for ID {id} and email {email}")
        except Exception as e:
            logger.exception(f'Error while inserting details: {e}')
            

def update_details(runid, otp, status):
    with conn.cursor() as cursor:
        update_query = """
        UPDATE user_details SET
        otp = %s, status = %s
        WHERE id = %s;
        """
        try:
            cursor.execute(update_query, (otp, status, runid))
            conn.commit()
            
            logger.info(f"Updated record for RunID {runid}")
        except Exception as e:
            logger.exception(f'Error while updating record: {e}')
            

def update_status(runid, status):
    with conn.cursor() as cursor:
        update_query = """
        UPDATE user_details SET
        status = %s
        WHERE id = %s;
        """
        try:
            cursor.execute(update_query, (status, runid))
            conn.commit()
            
            logger.info(f"Updated status for RunID {runid}")
        except Exception as e:
            logger.exception(f'Error while updating status: {e}')


def update_otp_ref(runid, otp_ref):
    with conn.cursor() as cursor:
        update_query = """
        UPDATE user_details SET
        otp_ref = %s
        WHERE id = %s;
        """
        try:
            cursor.execute(update_query, (otp_ref, runid))
            conn.commit()
            
            logger.info(f"Updated otp_ref for RunID {runid}")
        except Exception as e:
            logger.exception(f'Error while updating otp_ref: {e}')
            
            

    
def select_otp(id):
    with conn.cursor() as cursor:
        select_query = "SELECT otp FROM user_details WHERE id = %s;"
        cursor.execute(select_query, (id,))
        otp = cursor.fetchone()
          # Fetches the first row of the query result
        if otp:
            logger.info(f"Fetched OTP for ID {id}")
            return otp[0]
        else:
            logger.info(f"No OTP found for ID {id}")
            return None        
        

def get_otp_reference(id):
     with conn.cursor() as cursor:
        select_query = "SELECT otp_ref FROM user_details WHERE id = %s;"
        cursor.execute(select_query, (id,))
        otp_ref = cursor.fetchone()
          # Fetches the first row of the query result
        if otp_ref:
            logger.info(f"Fetched OTP for ID {id}")
            return otp_ref[0]
        else:
            logger.info(f"No OTP found for ID {id}")
            return None          