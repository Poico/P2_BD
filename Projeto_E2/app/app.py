#!/usr/bin/python3
# Copyright (c) BDist Development Team
# Distributed under the terms of the Modified BSD License.
import os
from logging.config import dictConfig
import random

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from psycopg.rows import namedtuple_row
from psycopg_pool import ConnectionPool

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)s - %(funcName)20s(): %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

app = Flask(__name__)
app.config.from_prefixed_env()
log = app.logger
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=RATELIMIT_STORAGE_URI,
)

# Use the DATABASE_URL environment variable if it exists, otherwise use the default.
# Use the format postgres://username:password@hostname/database_name to connect to the database.
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://airline:airline@postgres/airline")
#user airline password airline
#db airline

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    kwargs={
        "autocommit": True,  # If True don’t start transactions automatically.
        "row_factory": namedtuple_row,
    },
    min_size=4,
    max_size=10,
    open=True,
    # check=ConnectionPool.check_connection,
    name="postgres_pool",
    timeout=5,
)


def is_decimal(s):
    """Returns True if string is a parseable float number."""
    try:
        float(s)
        return True
    except ValueError:
        return False

# Ex1: Lista todos os aeroportos (nome e cidade).
@app.route("/", methods=("GET",))
def list_aeroports():
    """Show the list of airports."""

    with pool.connection() as conn:
        with conn.cursor() as cur:
            airports = cur.execute(
                """
                SELECT nome, cidade
                FROM aeroporto
                """,
                {},
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    return jsonify(airports), 200


# Exercicio 2:Lista todos os voos (número de série do avião, hora de partida
# e aeroporto de chegada) que partem do aeroporto de
# <partida> até 12h após o momento da consulta.


@app.route("/voos/<partida>", methods=("GET",))
@limiter.limit("1 per second")
def show_next_flights(partida):
    """Show all flights that leave airport partida in the next 12 hours."""

    with pool.connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """SELECT nome, cidade
                FROM aeroporto
                WHERE codigo = %(partida)s;""",
                {"partida": partida},
            )
            if not cur.rowcount:
                return jsonify({"message": "Aeroporto não encontrado.", "status": "error"}), 404


            aeroportos = cur.execute(
                """
                SELECT no_serie, hora_partida, chegada
                FROM voo
                WHERE partida = %(partida)s
                AND hora_partida > NOW()
                AND hora_partida < NOW() + INTERVAL '12 hours'
                ORDER BY hora_partida;
                """,
                {"partida": partida}
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    return jsonify(aeroportos), 200

@app.route("/voos/<partida>/<chegada>/", methods=("GET",))
@limiter.limit("1 per second")
def show_next_flights_between(partida,chegada):
    """Show the first 3 flights that leave airport partida and arrive at airport chegada,"""

    with pool.connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """SELECT nome, cidade
                FROM aeroporto
                WHERE codigo = %(partida)s OR codigo = %(chegada)s;""",
                {"partida": partida, "chegada": chegada},
            )
            if cur.rowcount < 2:
                return jsonify({"message": "Aeroporto não encontrado.", "status": "error"}), 404

            voos = cur.execute(
                """
                SELECT v.no_serie, v.hora_partida
                FROM voo v
                WHERE v.partida = %(partida)s
                AND v.chegada = %(chegada)s
                AND v.hora_partida > NOW()
                AND (
                    SELECT COUNT(*) FROM assento a WHERE a.no_serie = v.no_serie
                ) >
                (
                    SELECT COUNT(*) FROM bilhete b WHERE b.voo_id = v.id
                )
                ORDER BY v.hora_partida
                LIMIT 3;
                """,
                {
                    "partida": partida,
                    "chegada": chegada
                },
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    return jsonify(voos), 200


@app.route("/compra/<voo>/", methods=("POST",))
@limiter.limit("1 per second")
def buy_ticket(voo):
    """" Faz uma compra de um ou mais bilhetes para o <voo>, 
    populando as tabelas <venda> e <bilhete>. 
    Recebe como argumentos o nif do cliente, 
    e uma lista de pares 
    (nome de passageiro, classe bilhete) 
    especificando os bilhetes a comprar.
    """
    # ja previne sql injection pois o psycopg automaticamente 
    # escapa chars especiais e formate os dados antes de mandar para a BD
    # e porque também não fazemos a concatenação direta de strings
    data = request.get_json()
    nif = data.get("nif")
    passageiros = data.get("passageiros")
    num_1c = 0
    num_2c = 0

    for passageiro in passageiros:
        classe = passageiro.get("classe")
        if classe:
            num_1c+= 1
        else:
            num_2c+= 1

    if not data or not nif or not passageiros:
        return jsonify({"message": "NIF e lista de passageiros necessários.", "status": "error"}), 400

    with pool.connection() as conn:
        try:
            with conn.transaction(): # start transaction
                with conn.cursor() as cur:
                    #check if flight exists and is not departed and has available seats
                    cur.execute(
                        """
                        SELECT id
                        FROM voo
                        WHERE id = %(voo)s
                        AND hora_partida > NOW();
                        """,
                        {"voo": voo},
                    )
                    row = cur.fetchone()
                    if not row:
                        return jsonify({"message": "Voo não encontrado ou já descolou.", "status": "error"}), 404
                    
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM assento
                        WHERE no_serie = (
                            SELECT no_serie
                            FROM voo
                            WHERE id = %(voo)s
                        )
                        AND prim_classe = TRUE
                        AND lugar NOT IN (
                            SELECT lugar
                            FROM bilhete
                            WHERE voo_id = %(voo)s
                        );
                        """,
                        {"voo": voo},
                    )
                    row = cur.fetchone()

                    if row[0] < num_1c:
                        return jsonify({"message": "Não há assentos de primeira classe suficientes.", "status": "error"}), 400
                    
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM assento
                        WHERE no_serie = (
                            SELECT no_serie
                            FROM voo
                            WHERE id = %(voo)s
                        )
                        AND prim_classe = FALSE
                        AND lugar NOT IN (
                            SELECT lugar
                            FROM bilhete
                            WHERE voo_id = %(voo)s
                        );
                        """,
                        {"voo": voo},
                    )
                    row = cur.fetchone()

                    if row[0] < num_2c:
                        return jsonify({"message": "Não há assentos de segunda classe suficientes", "status": "error"}), 400
                    
                    cur.execute(
                       """INSERT INTO venda (nif_cliente, balcao, hora) 
                       VALUES(%(nif)s, NULL, NOW())
                       RETURNING codigo_reserva;""",
                       {"nif": nif},
                    )
                    codigo_reserva = cur.fetchone().codigo_reserva
                    log.debug(f"Inserted sale with code {codigo_reserva}.")

                    bilhetes = []
                    for passageiro in passageiros:
                        nome_passageiro = passageiro.get("nome")
                        prim_classe = passageiro.get("classe")

                        if not nome_passageiro:
                           return jsonify({"message": "Nome de passageiro necessário.", "status": "error"}), 400

                        if not prim_classe:
                           preco = random.randint(100,300)
                        else:
                            preco = random.randint(300,600)
                       
                        cur.execute("""
                            INSERT INTO bilhete (voo_id, codigo_reserva, nome_passageiro, preco, prim_classe)
                            VALUES (%(voo)s, %(codigo_reserva)s, %(nome_passageiro)s, %(preco)s, %(prim_classe)s)
                            RETURNING id;     
                            """,
                            {
                                "voo":voo,
                                "codigo_reserva": codigo_reserva,
                                "nome_passageiro": nome_passageiro,
                                "prim_classe": prim_classe,
                                "preco": preco
                            },
                        )
                        bilhete_id = cur.fetchone().id
                        bilhetes.append(bilhete_id)
        except Exception as e:
            return jsonify({"message": str(e), "status": "error"}), 500
    return jsonify({"message": "Compra realizada com sucesso!", "bilhetes": bilhetes, "status": "success"}), 200


@app.route("/checkin/<bilhete>", methods=("POST",))
@limiter.limit("1 per second")
def checkin(bilhete):
    """Faz o check-in de um bilhete, atribuindo-lhe automaticamente um assento da classe correspondente."""
    #Verificar se o check-in é possivel, ou seja, se o voo ainda não partiu e se o bilhete existe.
    with pool.connection() as conn:
        try:
            with conn.transaction(): # start transaction
                with conn.cursor() as cur:
                    # Get bilhete info
                    cur.execute(
                        """
                        SELECT voo_id, prim_classe
                        FROM bilhete
                        WHERE id = %(bilhete)s;
                        """,
                        {"bilhete": bilhete},
                    )
                    row = cur.fetchone()
                    if not row:
                        return jsonify({"message": "Bilhete não encontrado.", "status": "error"}), 404
                    voo_id, prim_classe = row.voo_id, row.prim_classe

                    cur.execute(
                        """
                        SELECT id
                        FROM voo
                        WHERE id = %(voo)s
                        AND hora_partida > NOW();
                        """,
                        {"voo": voo_id},
                    )
                    row = cur.fetchone()
                    if not row:
                        return jsonify({"message": "Voo não encontrado ou já descolou.", "status": "error"}), 404

                    # sacar assentos disponiveis do voo com o no_serie
                    cur.execute(
                        """SELECT no_serie
                        FROM voo
                        WHERE id = %(voo_id)s;
                        """,
                        {"voo_id": voo_id},
                    )
                    row = cur.fetchone()
                    no_serie = row.no_serie
                    cur.execute(
                        """SELECT lugar
                        FROM assento
                        WHERE no_serie = %(no_serie)s
                        AND prim_classe = %(classe)s
                        AND lugar NOT IN (
                            SELECT lugar
                            FROM bilhete
                            WHERE voo_id = %(voo_id)s
                            AND lugar IS NOT NULL
                        )
                        LIMIT 1;
                        """,
                        {
                            "no_serie": no_serie,
                            "classe": prim_classe,
                            "voo_id": voo_id,
                        }
                    )
                    row = cur.fetchone()
                    if not row:
                        return jsonify({"message": "Sem assentos livres.", "row": row, "status": "error"}), 404
                    lugar = row.lugar

                    cur.execute(
                        """
                        UPDATE bilhete
                        SET lugar = %(lugar)s,
                        no_serie = %(no_serie)s
                        WHERE id = %(bilhete)s;
                        """,
                        {"lugar": lugar, 
                         "bilhete": bilhete,
                         "no_serie": no_serie
                        },
                    )
        except Exception as e:
            return jsonify({"message": str(e), "status": "error"}), 500
    return jsonify({"message": "Check-in realizado com sucesso!", "status": "success"}), 200

if __name__ == "__main__":
    app.run()
