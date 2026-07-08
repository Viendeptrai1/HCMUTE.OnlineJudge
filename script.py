import psycopg
conn = psycopg.connect('postgresql://oj:oj_password@localhost:5432/oj', autocommit=True)
conn.execute("ALTER TYPE submission_language RENAME VALUE 'c' TO 'C'")
conn.execute("ALTER TYPE submission_language RENAME VALUE 'java' TO 'JAVA'")
print('Done!')
