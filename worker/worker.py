import json
import os
import time

import redis
import psycopg2


def get_redis():
    while True:
        try:
            r = redis.Redis(
                host=os.getenv('REDIS_HOST', 'redis'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=0,
                socket_timeout=5,
            )
            r.ping()
            return r
        except redis.exceptions.ConnectionError as e:
            print("Waiting for redis...", e)
            time.sleep(2)


def get_db_conn():
    while True:
        try:
            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'db'),
                port=os.getenv('POSTGRES_PORT', 5432),
                dbname=os.getenv('POSTGRES_DB', 'postgres'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
            )
            return conn
        except psycopg2.OperationalError as e:
            print("Waiting for postgres...", e)
            time.sleep(2)


def ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id VARCHAR(256) NOT NULL UNIQUE,
                vote VARCHAR(1) NOT NULL
            )
        """)
        conn.commit()


def main():
    r = get_redis()
    conn = get_db_conn()
    ensure_schema(conn)
    print("Worker started, waiting for votes...")

    while True:
        item = r.blpop('votes', timeout=5)
        if not item:
            continue
        _, data = item
        vote = json.loads(data)
        voter_id, choice = vote['voter_id'], vote['vote']
        print(f"Processing vote for '{choice}' by {voter_id}")
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO votes (id, vote) VALUES (%s, %s)
                ON CONFLICT (id) DO UPDATE SET vote = EXCLUDED.vote
                """,
                (voter_id, choice),
            )
            conn.commit()


if __name__ == "__main__":
    main()
