import os
import glob
import psycopg2
from dotenv import load_dotenv

def get_env() -> dict:
    """ get env variables and store it into a dict then return it """

    load_dotenv("../.env")
    env_dict = {}
    env_dict["DB_NAME"] = os.getenv("POSTGRES_DB")
    env_dict["DB_USER"] = os.getenv("POSTGRES_USER")
    env_dict["DB_PASSWORD"] = os.getenv("POSTGRES_PASSWORD")
    env_dict["DB_HOST"] = os.getenv("POSTGRES_HOST")
    env_dict["DB_PORT"] = os.getenv("POSTGRES_PORT")
    iterator = iter(env_dict)

    while True:
        try:
            key = next(iterator) 
            if env_dict[key] == None:
                print("One or few keys are missing")
                exit()
        except StopIteration:
            break  

    return env_dict

def combine_tables_into_customers(cur, conn):
    print("Updating customers table...")

    cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS category_id BIGINT")
    cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS category_code TEXT")
    cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS brand TEXT")

    cur.execute("""
        UPDATE customers c
        SET category_id = i.category_id,
            category_code = i.category_code,
            brand = i.brand
        FROM items i
        WHERE c.product_id = i.product_id;
    """)

    conn.commit()
    print("Customers table updated successfully! ✅")

def connect_to_db(env_dict: dict, path: list = None):
    try:
        conn = psycopg2.connect(
            dbname=env_dict["DB_NAME"],
            user=env_dict["DB_USER"],
            password=env_dict["DB_PASSWORD"],
            host=env_dict["DB_HOST"],
            port=env_dict["DB_PORT"]
        )
        cur = conn.cursor()
        combine_tables_into_customers(cur, conn)

    except Exception as e:
        print(f"Error while removing duplicates : {e}❌")

    finally:
        # Close the connection
        if cur:
            cur.close()
        if conn:
            conn.close()


            
def main():
    env_dict = get_env()
    connect_to_db(env_dict)

if __name__ == "__main__":
    main()