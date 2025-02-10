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

def trim_folder_and_extension(path: str) -> str:
    path = path.split("/")[-1]
    return path.replace(".csv", "")

def csv_checker(path: list, filenames_with_path: list):
    if path is not None and not any(item in filenames_with_path for item in path):
        print(f"The path is incorrect -> {path}")
        exit()
    elif path == None and not filenames_with_path:
        print("NO CSV files found.")
        exit()    
    print("CSV checked!✅")
    
def get_filenames_with_path(path: list) -> list:
    filenames_with_path = glob.glob('../customer/*.csv')
    filenames_with_path = [f.replace("\\", "/") for f in filenames_with_path]
    csv_checker(path, filenames_with_path)

    return filenames_with_path

def add_tables(cur, conn, filenames_with_path):
    occurence = 0
    for file in filenames_with_path:
            table_name = trim_folder_and_extension(file)
            print(f"Creating '{table_name}' table ...")
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                event_time TIMESTAMPTZ,
                event_type VARCHAR(255),
                product_id INT,
                price DECIMAL(10, 2),
                user_id BIGINT,
                user_session UUID
            );
            """
            cur.execute(create_table_query)
            print(f"Successfully created table '{table_name}'! ✅")
            print(f"Transferring data to table'{table_name}'...")
            with open(file, 'r') as f:
                cur.copy_expert(f"COPY {table_name}(event_time, event_type, product_id, price, user_id, user_session) FROM STDIN WITH CSV HEADER", f)
            conn.commit()
            print(f"Data transferred successfully to table '{table_name}'! ✅")
            join_all_datas(cur, conn, table_name, occurence)
            occurence = 1

def drop_all_tables(cur, conn):
    cur.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public';
        """)
    tables = cur.fetchall()

    if not tables:
        print("✅ No tables found. Database is already empty.")
    else:
        for table in tables:
            cur.execute(f"DROP TABLE IF EXISTS {table[0]} CASCADE;")
            print(f"🗑️ Dropped table: {table[0]}")
        conn.commit()
        print("All tables have been successfully deleted! ✅")


def join_all_datas(cur, conn, current_table_name: str, occurence: int):
    if occurence == 0:
        print(f"Creating customers table...")
        cur.execute(f"""
            CREATE TABLE customers AS
            SELECT * FROM {current_table_name};
            """)
        conn.commit()
        print(f"Successfully created table customers! ✅")        
    else:
        print(f" Joining {current_table_name}'s data into customers table...")
        cur.execute(f"""
        INSERT INTO customers
        SELECT * FROM {current_table_name};
        """)
        conn.commit()
        print(f"{current_table_name}'s data joined with sucess! ✅")

def delete_duplicate(cur, conn):
    table_name = "customers"
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
    columns = [row[0] for row in cur.fetchall()]
    group_by_columns = ", ".join(columns)
    cur.execute(f"""
        WITH ranked AS (
            SELECT 
                ctid, {group_by_columns},
                ROW_NUMBER() OVER (PARTITION BY {group_by_columns} ORDER BY ctid) AS row_num
            FROM {table_name}
        )
        DELETE FROM {table_name} 
        WHERE ctid IN (SELECT ctid FROM ranked WHERE row_num > 1);
    """)
    
    print(f"Removing duplicates from {table_name} table...")
    conn.commit()
    print("Duplicate(s) deleted sucessfully !🗑️")

def show_duplicate(cur):
    table_name = "customers"
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
    columns = [row[0] for row in cur.fetchall()]

    group_by_columns = ", ".join(columns)

    cur.execute(f"""
        SELECT {group_by_columns}, COUNT(*) 
        FROM {table_name}
        GROUP BY {group_by_columns}
        HAVING COUNT(*) > 1;
    """)
    duplicates = cur.fetchall()

    print("Duplicates:")
    if not duplicates:
        print("No duplicates found!")
        return
    
    which = input("Please choose an option:\n"
                "1 - Show only the number of duplicates\n"
                "2 - Show the lines\n"
                "  - Both\n")
    if which == "1":
        print(len(duplicates), "duplicates found!")
    elif which == "2":
        for row in duplicates:
            print(row)
    else:
        print(len(duplicates), "duplicates found!")
        for row in duplicates:
            print(row)

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
        delete_duplicate(cur, conn)
        #show_duplicate(cur)

    except Exception as e:
        print(f"Error while joining tables : {e}❌")

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