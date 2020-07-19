import pandas as pd
import os
import ast
import psycopg2


def main():
    try:
        conn = psycopg2.connect(host="ec2-52-71-231-180.compute-1.amazonaws.com", database="d5hfdk5kpf20ue", user="xnbyqsnbksglye", password="07c5f98c1b777543e2b569dff293c829866056c8362da18ecf8db3cb99277e83")
        cur = conn.cursor()

        dir = os.path.dirname(__file__)
        list = pd.read_csv(dir + "/app/data/animes.csv", header=0, usecols=["title", "synopsis", "genre", "img_url"])
        list_clean = list.drop_duplicates(subset=["title"])

        for anime in list_clean.itertuples(index=False, name=None):
            genres = ast.literal_eval(anime[2])
            genres = [n.strip() for n in genres]
            cur.execute('insert into show (title, description, genre, type, image) values (%s, %s, %s, %s, %s)', (anime[0], anime[1], genres, "anime", anime[3]))

        conn.commit()
        cur.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)


if __name__ == "__main__":
    main()